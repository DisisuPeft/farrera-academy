from datetime import date

from rest_framework.test import APIClient

from capacitacion.models import Inscripcion, Periodo
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase


class ForzarFinalizacionEndpointTests(CapacitacionTestBase):
    """T027: endpoint administrativo para FinalizacionService.forzar."""

    def setUp(self):
        self.client = APIClient()
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

    def test_admin_puede_forzar_la_finalizacion(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.post(f'/api/capacitacion/inscripciones/{self.inscripcion.id}/forzar/')
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.data['completado_at'])
        self.inscripcion.refresh_from_db()
        self.assertIsNotNone(self.inscripcion.completado_at)

    def test_colaborador_no_puede_forzar_la_finalizacion(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.post(f'/api/capacitacion/inscripciones/{self.inscripcion.id}/forzar/')
        self.assertEqual(resp.status_code, 403)
        self.inscripcion.refresh_from_db()
        self.assertIsNone(self.inscripcion.completado_at)
