from datetime import date

from rest_framework.test import APIClient

from capacitacion.models import Evaluacion, Inscripcion, Periodo, Pregunta, OpcionPregunta
from capacitacion.services.evidencia_service import EvidenciaService
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase
from catalogos.models import TipoEvaluacion


class IntentosMaximosEvaluacionTests(CapacitacionTestBase):
    """Evaluacion.intentos_maximos (default 3) limita cuántos intentos puede
    registrar un colaborador para una misma evaluación — configurable por
    evaluación, no fijo en código. Antes de esto, el backend aceptaba
    intentos ilimitados (solo el frontend bloqueaba, como confirmó el
    usuario); ahora el backend es la fuente de verdad del límite."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tipo_evaluacion = TipoEvaluacion.objects.create(nombre='Examen', codigo='examen-intentos-test')

    def setUp(self):
        self.client = APIClient()
        periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        self.inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo)
        self.assertIsInstance(self.inscripcion, Inscripcion)

    def _crear_evaluacion(self, intentos_maximos=3):
        evaluacion = Evaluacion.objects.create(
            titulo='Evaluación módulo', tipo=self.tipo_evaluacion,
            modulo=self.modulo_a, intentos_maximos=intentos_maximos,
        )
        pregunta = Pregunta.objects.create(evaluacion=evaluacion, texto='¿Pregunta?', orden=1)
        opcion_correcta = OpcionPregunta.objects.create(pregunta=pregunta, texto='Sí', orden=1, es_correcta=True)
        OpcionPregunta.objects.create(pregunta=pregunta, texto='No', orden=2, es_correcta=False)
        return evaluacion, pregunta, opcion_correcta

    def test_default_es_3_intentos(self):
        evaluacion = Evaluacion.objects.create(
            titulo='Evaluación default', tipo=self.tipo_evaluacion, modulo=self.modulo_a,
        )
        self.assertEqual(evaluacion.intentos_maximos, 3)

    def test_registrar_resultado_respeta_el_limite_configurado(self):
        evaluacion, _, _ = self._crear_evaluacion(intentos_maximos=2)

        primero = EvidenciaService.registrar_resultado_evaluacion(
            colaborador=self.colaborador, evaluacion=evaluacion, correctas=0, total=1,
        )
        segundo = EvidenciaService.registrar_resultado_evaluacion(
            colaborador=self.colaborador, evaluacion=evaluacion, correctas=0, total=1,
        )
        tercero = EvidenciaService.registrar_resultado_evaluacion(
            colaborador=self.colaborador, evaluacion=evaluacion, correctas=0, total=1,
        )

        from capacitacion.models import ResultadoEvaluacion
        self.assertIsInstance(primero, ResultadoEvaluacion)
        self.assertIsInstance(segundo, ResultadoEvaluacion)
        self.assertEqual(tercero.__class__.__name__, 'IntentosAgotados')

    def test_endpoint_devuelve_400_al_agotar_intentos(self):
        evaluacion, pregunta, opcion_correcta = self._crear_evaluacion(intentos_maximos=1)
        self.client.force_authenticate(self.colaborador)
        payload = {'evaluacion': evaluacion.id, 'respuestas': [{'pregunta': pregunta.id, 'opcion': opcion_correcta.id}]}

        primero = self.client.post('/api/capacitacion/mis-resultados/', payload, format='json')
        self.assertEqual(primero.status_code, 201)

        segundo = self.client.post('/api/capacitacion/mis-resultados/', payload, format='json')
        self.assertEqual(segundo.status_code, 400)
        self.assertIn('intentos', segundo.data['detail'].lower())

    def test_intentos_maximos_mas_altos_permiten_mas_reintentos(self):
        evaluacion, _, _ = self._crear_evaluacion(intentos_maximos=5)

        from capacitacion.models import ResultadoEvaluacion
        for _ in range(5):
            resultado = EvidenciaService.registrar_resultado_evaluacion(
                colaborador=self.colaborador, evaluacion=evaluacion, correctas=0, total=1,
            )
            self.assertIsInstance(resultado, ResultadoEvaluacion)

        sexto = EvidenciaService.registrar_resultado_evaluacion(
            colaborador=self.colaborador, evaluacion=evaluacion, correctas=0, total=1,
        )
        self.assertEqual(sexto.__class__.__name__, 'IntentosAgotados')
