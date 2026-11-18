from datetime import date

from rest_framework.test import APIClient

from capacitacion.models import Evaluacion, Inscripcion, Periodo, ResultadoEvaluacion
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase
from catalogos.models import TipoEvaluacion


class ProgresoVisualExigeAprobadoNoSoloIntentadoTests(CapacitacionTestBase):
    """El progreso visual (CursoColaboradorSerializer/ModuloColaboradorSerializer)
    debe marcar una evaluación como 'completada' solo si al menos un intento
    alcanzó el puntaje_minimo — no por el mero hecho de haberla intentado.
    Antes del fix, un intento reprobado ya hacía avanzar la barra de progreso,
    aunque FinalizacionService (el criterio real de acreditación) exigiera
    aprobar. Esa divergencia rompía la auditoría: el colaborador veía 100% de
    progreso sin haber aprobado nada."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.modulo_a.tiene_evaluacion = True
        cls.modulo_a.save(update_fields=['tiene_evaluacion'])
        cls.tipo_evaluacion = TipoEvaluacion.objects.create(nombre='Examen', codigo='examen-test')
        cls.evaluacion_modulo = Evaluacion.objects.create(
            titulo='Evaluación módulo 1', tipo=cls.tipo_evaluacion,
            modulo=cls.modulo_a, puntaje_minimo=70,
        )

    def setUp(self):
        self.client = APIClient()
        periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        self.inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo)
        self.assertIsInstance(self.inscripcion, Inscripcion)

    def _progreso_modulo(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.get(f'/api/capacitacion/ver/modulos/?curso={self.curso_a.id}')
        self.assertEqual(resp.status_code, 200)
        modulo_data = next(m for m in resp.data['results'] if m['id'] == self.modulo_a.id)
        return modulo_data['progreso']

    def test_intento_reprobado_no_marca_la_evaluacion_como_completada(self):
        ResultadoEvaluacion.objects.create(
            inscripcion=self.inscripcion, evaluacion=self.evaluacion_modulo,
            correctas=2, total=10,
        )

        progreso = self._progreso_modulo()

        self.assertEqual(progreso['completados'], 0)

    def test_intento_aprobado_si_marca_la_evaluacion_como_completada(self):
        ResultadoEvaluacion.objects.create(
            inscripcion=self.inscripcion, evaluacion=self.evaluacion_modulo,
            correctas=8, total=10,
        )

        progreso = self._progreso_modulo()

        self.assertEqual(progreso['completados'], 1)

    def test_reprobar_y_luego_aprobar_en_un_reintento_si_marca_completada(self):
        ResultadoEvaluacion.objects.create(
            inscripcion=self.inscripcion, evaluacion=self.evaluacion_modulo,
            correctas=2, total=10,
        )
        ResultadoEvaluacion.objects.create(
            inscripcion=self.inscripcion, evaluacion=self.evaluacion_modulo,
            correctas=9, total=10,
        )

        progreso = self._progreso_modulo()

        self.assertEqual(progreso['completados'], 1)
