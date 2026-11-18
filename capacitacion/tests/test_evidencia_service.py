from datetime import date

from catalogos.models import CatalogStatus, TipeTema, TipoEvaluacion
from capacitacion.models import (
    ContenidoBloque, ContenidoBloqueOpcion, ContenidoBloqueRespuesta,
    Curso, Evaluacion, Inscripcion, Modulo, Periodo, ProgresoTema, ResultadoEvaluacion, Tema,
)
from capacitacion.services.evidencia_service import ContenidoAjeno, EvidenciaService
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase


class EvidenciaServiceRegistrarProgresoTests(CapacitacionTestBase):
    """T012: EvidenciaService.registrar_progreso rechaza un tema que no
    pertenece al curso de la inscripción (AC8)."""

    def setUp(self):
        self.periodo_a = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo_a)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

        self.curso_b = Curso.objects.create(
            titulo='Curso de B', status=self.status_publicado, empresa=self.empresa_a,
        )
        self.modulo_b = Modulo.objects.create(curso=self.curso_b, titulo='Módulo 1', orden=1)
        self.tema_b = Tema.objects.create(modulo=self.modulo_b, titulo='Tema 1', tipo=self.tipo_tema, orden=1)

    def test_rechaza_tema_que_no_pertenece_al_curso_de_la_inscripcion(self):
        resultado = EvidenciaService.registrar_progreso(colaborador=self.colaborador, tema=self.tema_b)
        self.assertIsInstance(resultado, ContenidoAjeno)
        self.assertFalse(ProgresoTema.objects.filter(inscripcion=self.inscripcion, tema=self.tema_b).exists())

    def test_resuelve_por_curso_no_por_inscripcion_mas_reciente(self):
        """Una segunda inscripción activa a OTRO curso (más reciente) no debe
        impedir registrar progreso legítimo en la primera — la resolución es
        por curso del contenido, no por 'la última inscripción' sin más."""
        periodo_b = Periodo.objects.create(
            curso=self.curso_b, nombre='Convocatoria 1', fecha_inicio=date(2026, 2, 1),
        )
        inscripcion_b = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo_b)
        self.assertIsInstance(inscripcion_b, Inscripcion)
        self.assertGreater(inscripcion_b.inscrito_at, self.inscripcion.inscrito_at)

        tema_a2 = Tema.objects.create(modulo=self.modulo_a, titulo='Tema 2', tipo=self.tipo_tema, orden=2)
        resultado = EvidenciaService.registrar_progreso(colaborador=self.colaborador, tema=tema_a2)
        self.assertIsInstance(resultado, ProgresoTema)
        self.assertEqual(resultado.inscripcion, self.inscripcion)


class EvidenciaServiceProgresoIndependientePorInscripcionTests(CapacitacionTestBase):
    """T016: dos inscripciones del mismo colaborador al mismo curso en
    periodos distintos mantienen progreso independiente (AC4)."""

    def setUp(self):
        self.periodo_1 = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        self.inscripcion_1 = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo_1)
        self.assertIsInstance(self.inscripcion_1, Inscripcion)

    def test_progreso_de_la_primera_inscripcion_no_se_altera_al_registrar_en_la_segunda(self):
        resultado_1 = EvidenciaService.registrar_progreso(colaborador=self.colaborador, tema=self.tema_a)
        self.assertIsInstance(resultado_1, ProgresoTema)
        self.assertEqual(resultado_1.inscripcion, self.inscripcion_1)

        periodo_2 = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 2', fecha_inicio=date(2026, 2, 1),
        )
        inscripcion_2 = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo_2)
        self.assertIsInstance(inscripcion_2, Inscripcion)
        self.assertGreater(inscripcion_2.inscrito_at, self.inscripcion_1.inscrito_at)

        resultado_2 = EvidenciaService.registrar_progreso(colaborador=self.colaborador, tema=self.tema_a)
        self.assertIsInstance(resultado_2, ProgresoTema)
        self.assertEqual(resultado_2.inscripcion, inscripcion_2)

        self.assertEqual(
            ProgresoTema.objects.filter(inscripcion=self.inscripcion_1, tema=self.tema_a).count(), 1,
        )
        self.assertEqual(
            ProgresoTema.objects.filter(inscripcion=inscripcion_2, tema=self.tema_a).count(), 1,
        )
        self.assertNotEqual(resultado_1.pk, resultado_2.pk)


class EvidenciaServiceRegistrarRespuestaBloqueTests(CapacitacionTestBase):
    """T014: EvidenciaService.registrar_respuesta_bloque rechaza una opción
    que no pertenece al bloque referenciado (AC9)."""

    def setUp(self):
        self.periodo_a = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo_a)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

        self.bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_opcion_multiple, orden=1)
        self.opcion = ContenidoBloqueOpcion.objects.create(bloque=self.bloque, orden=1, texto='Opción 1', es_correcta=True)

        otro_bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_opcion_multiple, orden=2)
        self.opcion_ajena = ContenidoBloqueOpcion.objects.create(
            bloque=otro_bloque, orden=1, texto='Ajena', es_correcta=True,
        )

    def test_rechaza_opcion_que_no_pertenece_al_bloque(self):
        resultado = EvidenciaService.registrar_respuesta_bloque(
            colaborador=self.colaborador, bloque=self.bloque, opcion=self.opcion_ajena,
        )
        self.assertIsInstance(resultado, ContenidoAjeno)
        self.assertFalse(
            ContenidoBloqueRespuesta.objects.filter(inscripcion=self.inscripcion, bloque=self.bloque).exists(),
        )

    def test_acepta_opcion_que_si_pertenece_al_bloque_y_calcula_es_correcta_en_servidor(self):
        resultado = EvidenciaService.registrar_respuesta_bloque(
            colaborador=self.colaborador, bloque=self.bloque, opcion=self.opcion,
        )
        self.assertIsInstance(resultado, ContenidoBloqueRespuesta)
        self.assertEqual(resultado.inscripcion, self.inscripcion)
        self.assertTrue(resultado.es_correcta)


class EvidenciaServiceRegistrarResultadoEvaluacionTests(CapacitacionTestBase):
    """T032: EvidenciaService.registrar_resultado_evaluacion rechaza una
    evaluación que no pertenece al curso de la inscripción activa (análogo
    a registrar_progreso/registrar_respuesta_bloque, AC4/AC8)."""

    def setUp(self):
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

        self.tipo_evaluacion = TipoEvaluacion.objects.create(nombre='Módulo', codigo='modulo-test')
        self.evaluacion = Evaluacion.objects.create(
            titulo='Evaluación 1', tipo=self.tipo_evaluacion, modulo=self.modulo_a,
        )

        self.curso_b = Curso.objects.create(
            titulo='Curso de B', status=self.status_publicado, empresa=self.empresa_a,
        )
        modulo_b = Modulo.objects.create(curso=self.curso_b, titulo='Módulo 1', orden=1)
        self.evaluacion_ajena = Evaluacion.objects.create(
            titulo='Evaluación ajena', tipo=self.tipo_evaluacion, modulo=modulo_b,
        )

    def test_rechaza_evaluacion_que_no_pertenece_al_curso_de_la_inscripcion(self):
        resultado = EvidenciaService.registrar_resultado_evaluacion(
            colaborador=self.colaborador, evaluacion=self.evaluacion_ajena, correctas=5, total=10,
        )
        self.assertIsInstance(resultado, ContenidoAjeno)
        self.assertFalse(
            ResultadoEvaluacion.objects.filter(inscripcion=self.inscripcion, evaluacion=self.evaluacion_ajena).exists(),
        )

    def test_acepta_evaluacion_que_si_pertenece_al_curso(self):
        resultado = EvidenciaService.registrar_resultado_evaluacion(
            colaborador=self.colaborador, evaluacion=self.evaluacion, correctas=8, total=10,
        )
        self.assertIsInstance(resultado, ResultadoEvaluacion)
        self.assertEqual(resultado.inscripcion, self.inscripcion)
        self.assertEqual(resultado.correctas, 8)
        self.assertEqual(resultado.total, 10)


class EvidenciaServiceInvocaFinalizacionServiceTests(CapacitacionTestBase):
    """T032: cada registrar_* invoca FinalizacionService.reevaluar después
    de guardar (postcondición del plan §3, pendiente desde T013 porque
    FinalizacionService no existía todavía en ese momento)."""

    def setUp(self):
        self.tema_a2 = Tema.objects.create(modulo=self.modulo_a, titulo='Tema 2', tipo=self.tipo_tema, orden=2)
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

    def test_registrar_progreso_finaliza_automaticamente_al_completar_el_ultimo_tema(self):
        EvidenciaService.registrar_progreso(colaborador=self.colaborador, tema=self.tema_a)
        self.inscripcion.refresh_from_db()
        self.assertIsNone(self.inscripcion.completado_at)

        EvidenciaService.registrar_progreso(colaborador=self.colaborador, tema=self.tema_a2)

        self.inscripcion.refresh_from_db()
        self.assertIsNotNone(self.inscripcion.completado_at)
