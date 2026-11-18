from datetime import date

from rest_framework.test import APIClient

from capacitacion.models import Inscripcion, Periodo, ProgresoTema, ResultadoEvaluacion
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase
from catalogos.models import TipoEvaluacion
from capacitacion.models import Evaluacion


class AdminProgresoResultadoEndpointsTests(CapacitacionTestBase):
    """T032: los endpoints administrativos de Inscripcion/ProgresoTema/
    ResultadoEvaluacion deben seguir respondiendo tras el cambio de
    `colaborador` directo a `inscripcion` (AC1, AC2)."""

    def setUp(self):
        self.client = APIClient()
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)
        tipo_evaluacion = TipoEvaluacion.objects.create(nombre='Módulo', codigo='modulo-test')
        evaluacion = Evaluacion.objects.create(titulo='Eval 1', tipo=tipo_evaluacion, modulo=self.modulo_a)
        ResultadoEvaluacion.objects.create(inscripcion=self.inscripcion, evaluacion=evaluacion, correctas=8, total=10)

    def test_admin_lista_inscripciones(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.get('/api/capacitacion/inscripciones/')
        self.assertEqual(resp.status_code, 200)

    def test_admin_lista_progresos_tema_con_filtro_de_colaborador(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.get(f'/api/capacitacion/progresos-tema/?colaborador={self.colaborador.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)
        self.assertIn('colaborador_nombre', resp.data['results'][0])

    def test_admin_lista_resultados_evaluacion_con_filtro_de_colaborador(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.get(f'/api/capacitacion/resultados-evaluacion/?colaborador={self.colaborador.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)
        self.assertIn('colaborador_nombre', resp.data['results'][0])
