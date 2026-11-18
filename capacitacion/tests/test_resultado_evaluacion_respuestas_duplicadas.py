from datetime import date

from rest_framework.test import APIClient

from catalogos.models import TipoEvaluacion
from capacitacion.models import Evaluacion, Inscripcion, OpcionPregunta, Periodo, Pregunta
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase


class RespuestasDuplicadasNoInflanCorrectasTests(CapacitacionTestBase):
    """T040 (cierre): MiResultadoEvaluacionSerializer.validate() comparaba
    conjuntos de preguntas (`set`), así que responder la misma pregunta dos
    veces no se detectaba como faltante — y la vista suma `es_correcta` sobre
    la lista cruda de respuestas, permitiendo que `correctas` > `total` real
    de preguntas de la evaluación (gap anotado desde T032/T037)."""

    def setUp(self):
        self.client = APIClient()
        periodo = Periodo.objects.create(curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1))
        self.inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo)
        self.assertIsInstance(self.inscripcion, Inscripcion)

        tipo_evaluacion = TipoEvaluacion.objects.create(nombre='Módulo', codigo='modulo-test')
        self.evaluacion = Evaluacion.objects.create(titulo='Eval 1', tipo=tipo_evaluacion, modulo=self.modulo_a)
        self.pregunta_1 = Pregunta.objects.create(evaluacion=self.evaluacion, texto='¿P1?', orden=1)
        self.pregunta_2 = Pregunta.objects.create(evaluacion=self.evaluacion, texto='¿P2?', orden=2)
        self.opcion_1_correcta = OpcionPregunta.objects.create(
            pregunta=self.pregunta_1, texto='Sí', orden=1, es_correcta=True,
        )
        self.opcion_2_correcta = OpcionPregunta.objects.create(
            pregunta=self.pregunta_2, texto='Sí', orden=1, es_correcta=True,
        )

    def test_duplicar_una_pregunta_ya_respondida_no_infla_correctas_por_encima_del_total(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/mis-resultados/', {
            'evaluacion': self.evaluacion.id,
            'respuestas': [
                {'pregunta': self.pregunta_1.id, 'opcion': self.opcion_1_correcta.id},
                {'pregunta': self.pregunta_1.id, 'opcion': self.opcion_1_correcta.id},
                {'pregunta': self.pregunta_2.id, 'opcion': self.opcion_2_correcta.id},
            ],
        }, format='json')

        self.assertEqual(resp.status_code, 400)
