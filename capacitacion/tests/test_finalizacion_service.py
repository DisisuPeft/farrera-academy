from datetime import date
from decimal import Decimal

from catalogos.models import CatalogStatus, TipoEvaluacion
from capacitacion.models import Curso, Evaluacion, Inscripcion, Modulo, Periodo, ProgresoTema, ResultadoEvaluacion, Tema
from capacitacion.services.finalizacion_service import FinalizacionService, YaFinalizada
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase


class FinalizacionServiceReevaluarConEvaluacionesTests(CapacitacionTestBase):
    """T018: FinalizacionService.reevaluar finaliza exactamente cuando se
    cumple el criterio con evaluaciones (todos los temas con progreso Y
    todas las evaluaciones del curso aprobadas), no antes (AC12, AC14)."""

    def setUp(self):
        self.tema_a2 = Tema.objects.create(modulo=self.modulo_a, titulo='Tema 2', tipo=self.tipo_tema, orden=2)
        self.tipo_evaluacion = TipoEvaluacion.objects.create(nombre='Módulo', codigo='modulo-test')
        self.evaluacion = Evaluacion.objects.create(
            titulo='Evaluación 1', tipo=self.tipo_evaluacion, modulo=self.modulo_a,
            puntaje_minimo=Decimal('70'),
        )
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

    def _completar_temas(self):
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a2)

    def test_no_finaliza_si_temas_completos_pero_evaluacion_no_aprobada(self):
        self._completar_temas()
        ResultadoEvaluacion.objects.create(
            inscripcion=self.inscripcion, evaluacion=self.evaluacion, correctas=5, total=10,
        )

        resultado = FinalizacionService.reevaluar(self.inscripcion)

        self.assertIsNone(resultado.completado_at)
        self.inscripcion.refresh_from_db()
        self.assertIsNone(self.inscripcion.completado_at)

    def test_finaliza_cuando_temas_completos_y_evaluacion_aprobada(self):
        self._completar_temas()
        ResultadoEvaluacion.objects.create(
            inscripcion=self.inscripcion, evaluacion=self.evaluacion, correctas=8, total=10,
        )

        resultado = FinalizacionService.reevaluar(self.inscripcion)

        self.assertIsNotNone(resultado.completado_at)
        self.inscripcion.refresh_from_db()
        self.assertIsNotNone(self.inscripcion.completado_at)


class FinalizacionServiceCursoSinEvaluacionesTests(CapacitacionTestBase):
    """T020: un curso sin ninguna evaluación asociada finaliza con solo el
    progreso completo de todos sus temas, sin ninguna acción adicional (AC13)."""

    def setUp(self):
        self.tema_a2 = Tema.objects.create(modulo=self.modulo_a, titulo='Tema 2', tipo=self.tipo_tema, orden=2)
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

    def test_finaliza_con_solo_progreso_completo_si_el_curso_no_tiene_evaluaciones(self):
        self.assertFalse(Evaluacion.objects.filter(
            curso=self.curso_a,
        ).exists() or Evaluacion.objects.filter(modulo__curso=self.curso_a).exists())

        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a2)

        resultado = FinalizacionService.reevaluar(self.inscripcion)

        self.assertIsNotNone(resultado.completado_at)
        self.inscripcion.refresh_from_db()
        self.assertIsNotNone(self.inscripcion.completado_at)

    def test_no_finaliza_si_falta_progreso_de_algun_tema_aunque_no_haya_evaluaciones(self):
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)

        resultado = FinalizacionService.reevaluar(self.inscripcion)

        self.assertIsNone(resultado.completado_at)


class FinalizacionServiceIdempotenciaTests(CapacitacionTestBase):
    """T022: reevaluar() sobre una inscripción ya finalizada es un no-op
    observable — no reevalúa el criterio ni modifica completado_at (AC6)."""

    def setUp(self):
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)
        primera = FinalizacionService.reevaluar(self.inscripcion)
        self.assertIsNotNone(primera.completado_at)
        self.completado_at_original = primera.completado_at

    def test_reevaluar_no_cambia_completado_at_aunque_el_criterio_ya_no_se_cumpla(self):
        """Propiedad adyacente, no la guarda de idempotencia en sí (esa la
        prueba el método siguiente): si después de finalizar se rompe la
        evidencia que la sustentaba (p.ej. se borra el progreso), una
        segunda llamada a reevaluar() no debe des-finalizar ni tocar el
        timestamp — una vez finalizada, queda finalizada. Esta prueba sigue
        en verde aunque se quite la guarda `completado_at is not None`,
        porque sin ella el criterio se re-evalúa, resulta falso, y no
        escribe nada igual."""
        ProgresoTema.objects.filter(inscripcion=self.inscripcion, tema=self.tema_a).delete()

        resultado = FinalizacionService.reevaluar(self.inscripcion)

        self.assertEqual(resultado.completado_at, self.completado_at_original)
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.completado_at, self.completado_at_original)

    def test_reevaluar_no_reescribe_completado_at_aunque_el_criterio_siga_cumplido(self):
        """Idempotencia real: incluso si el criterio TODAVÍA se cumple, una
        segunda llamada no debe recalcular/reescribir completado_at con un
        timestamp nuevo — debe retornar exactamente el mismo valor ya
        persistido, sin escritura adicional."""
        resultado = FinalizacionService.reevaluar(self.inscripcion)

        self.assertEqual(resultado.completado_at, self.completado_at_original)


class FinalizacionServiceForzarTests(CapacitacionTestBase):
    """T026: FinalizacionService.forzar produce el mismo resultado
    observable que una finalización automática, incluso cuando la
    inscripción NO cumple el criterio normal (AC15)."""

    def setUp(self):
        self.tema_a2 = Tema.objects.create(modulo=self.modulo_a, titulo='Tema 2', tipo=self.tipo_tema, orden=2)
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

    def test_forzar_finaliza_aunque_el_criterio_normal_no_se_cumpla(self):
        """Progreso incompleto a propósito (solo 1 de 2 temas) — una
        reevaluación automática NO finalizaría esto."""
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)

        resultado = FinalizacionService.forzar(self.inscripcion, actor=self.admin_a)

        self.assertIsNotNone(resultado.completado_at)
        self.inscripcion.refresh_from_db()
        self.assertIsNotNone(self.inscripcion.completado_at)

    def test_forzar_acredita_igual_que_una_finalizacion_automatica(self):
        from catalogos.models import NivelCompetencia
        from competencias.models import CompetenciaColaborador
        from competencias.models.competencia import Competencia, CompetenciaCurso

        nivel_2 = NivelCompetencia.objects.create(nombre='Nivel 2', codigo='nivel-2', orden=2)
        competencia = Competencia.objects.create(nombre='Competencia X', codigo='competencia-x')
        CompetenciaCurso.objects.create(competencia=competencia, curso=self.curso_a, nivel=nivel_2)

        FinalizacionService.forzar(self.inscripcion, actor=self.admin_a)

        registro = CompetenciaColaborador.objects.get(colaborador=self.colaborador, competencia=competencia)
        self.assertEqual(registro.nivel, nivel_2)
        self.assertEqual(registro.origen_id, self.inscripcion.id)

    def test_forzar_sobre_una_inscripcion_ya_finalizada_retorna_ya_finalizada(self):
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a2)
        primera = FinalizacionService.reevaluar(self.inscripcion)
        self.assertIsNotNone(primera.completado_at)

        resultado = FinalizacionService.forzar(self.inscripcion, actor=self.admin_a)

        self.assertIsInstance(resultado, YaFinalizada)
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.completado_at, primera.completado_at)


class FinalizacionServiceCursoSinTemasTests(CapacitacionTestBase):
    """Un curso sin ningún tema no puede finalizar vacuamente: 'todos los
    temas tienen progreso' no se cumple por no tener ninguno que cumplir."""

    def test_no_finaliza_un_curso_sin_ningun_tema(self):
        curso_vacio = Curso.objects.create(
            titulo='Curso vacío', status=self.status_publicado, empresa=self.empresa_a,
        )
        periodo = Periodo.objects.create(
            curso=curso_vacio, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo)
        self.assertIsInstance(inscripcion, Inscripcion)

        resultado = FinalizacionService.reevaluar(inscripcion)

        self.assertIsNone(resultado.completado_at)

    def test_tema_desactivado_no_bloquea_la_finalizacion(self):
        """Cierre (closing review): `_criterio_cumplido` no filtraba por
        `Tema.activo`, a diferencia de los serializers de progreso del
        colaborador (que sí lo hacen) — un tema desactivado DESPUÉS de que
        el colaborador ya completó todo lo visible podía dejar el curso sin
        poder finalizar nunca, mientras la UI del colaborador mostraba 100%."""
        curso = Curso.objects.create(
            titulo='Curso con tema desactivado', status=self.status_publicado, empresa=self.empresa_a,
        )
        modulo = Modulo.objects.create(curso=curso, titulo='M', orden=1)
        tema_visible = Tema.objects.create(modulo=modulo, titulo='Visible', tipo=self.tipo_tema, orden=1)
        tema_desactivado = Tema.objects.create(
            modulo=modulo, titulo='Desactivado', tipo=self.tipo_tema, orden=2, activo=False,
        )
        periodo = Periodo.objects.create(
            curso=curso, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo)
        self.assertIsInstance(inscripcion, Inscripcion)

        ProgresoTema.objects.create(inscripcion=inscripcion, tema=tema_visible)

        resultado = FinalizacionService.reevaluar(inscripcion)

        self.assertIsNotNone(resultado.completado_at)
        self.assertFalse(ProgresoTema.objects.filter(inscripcion=inscripcion, tema=tema_desactivado).exists())
