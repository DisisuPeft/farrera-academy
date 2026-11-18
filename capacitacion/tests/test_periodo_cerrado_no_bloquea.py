from datetime import date

from capacitacion.models import Inscripcion, Periodo, ProgresoTema, Tema
from capacitacion.services.evidencia_service import ContenidoAjeno, EvidenciaService
from capacitacion.services.finalizacion_service import FinalizacionService
from capacitacion.services.inscripcion_service import InscripcionService, PeriodoNoAbierto
from capacitacion.tests.base import CapacitacionTestBase, hacer_usuario


class PeriodoCerradoNoBloqueaInscripcionesExistentesTests(CapacitacionTestBase):
    """T030: cerrar un periodo no bloquea progreso/finalización de
    inscripciones ya existentes en él — solo nuevas inscripciones a ese
    periodo (AC16, AC17)."""

    def setUp(self):
        self.tema_a2 = Tema.objects.create(modulo=self.modulo_a, titulo='Tema 2', tipo=self.tipo_tema, orden=2)
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

        self.periodo.estado = Periodo.Estado.CERRADO
        self.periodo.save(update_fields=['estado'])

    def test_registrar_progreso_sigue_funcionando_tras_cerrar_el_periodo(self):
        resultado = EvidenciaService.registrar_progreso(colaborador=self.colaborador, tema=self.tema_a)

        self.assertIsInstance(resultado, ProgresoTema)
        self.assertNotIsInstance(resultado, ContenidoAjeno)

    def test_finalizacion_sigue_funcionando_tras_cerrar_el_periodo(self):
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a2)

        resultado = FinalizacionService.reevaluar(self.inscripcion)

        self.assertIsNotNone(resultado.completado_at)

    def test_nueva_inscripcion_al_periodo_cerrado_si_es_rechazada(self):
        otro_colaborador = hacer_usuario(self.dependencia_a)

        resultado = InscripcionService.crear(colaborador=otro_colaborador, periodo=self.periodo)

        self.assertIsInstance(resultado, PeriodoNoAbierto)
