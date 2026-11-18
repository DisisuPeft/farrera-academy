from datetime import date

from rest_framework.test import APIClient

from capacitacion.models import Inscripcion, Periodo, ProgresoTema, Tema
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase


class GetInscritoGetProgresoInscripcionMasRecienteTests(CapacitacionTestBase):
    """T037: get_inscrito/get_progreso (CursoColaboradorSerializer) calculan
    sobre la inscripción más reciente del colaborador a ese curso, no sobre
    la unión de todas (spec Acceptance, horneado tras `analyze`)."""

    def setUp(self):
        self.client = APIClient()
        self.tema_a2 = Tema.objects.create(modulo=self.modulo_a, titulo='Tema 2', tipo=self.tipo_tema, orden=2)

        periodo_1 = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        self.inscripcion_1 = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo_1)
        self.assertIsInstance(self.inscripcion_1, Inscripcion)
        ProgresoTema.objects.create(inscripcion=self.inscripcion_1, tema=self.tema_a)
        ProgresoTema.objects.create(inscripcion=self.inscripcion_1, tema=self.tema_a2)

        periodo_2 = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 2', fecha_inicio=date(2026, 2, 1),
        )
        self.inscripcion_2 = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo_2)
        self.assertIsInstance(self.inscripcion_2, Inscripcion)

    def test_progreso_refleja_solo_la_inscripcion_mas_reciente_no_la_union(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.get('/api/capacitacion/ver/cursos/')
        self.assertEqual(resp.status_code, 200)

        curso_data = next(c for c in resp.data['results'] if c['id'] == self.curso_a.id)
        self.assertEqual(curso_data['progreso']['completados'], 0)

    def test_inscrito_refleja_la_inscripcion_mas_reciente_no_cualquiera_activa(self):
        self.inscripcion_2.activo = False
        self.inscripcion_2.save(update_fields=['activo'])

        self.client.force_authenticate(self.colaborador)
        resp = self.client.get('/api/capacitacion/ver/cursos/')
        self.assertEqual(resp.status_code, 200)

        curso_data = next(c for c in resp.data['results'] if c['id'] == self.curso_a.id)
        self.assertFalse(curso_data['inscrito'])
