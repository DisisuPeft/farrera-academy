from datetime import date

from rest_framework.test import APIClient

from capacitacion.models import Inscripcion, Periodo
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase
from catalogos.models import NivelCompetencia
from competencias.models import CompetenciaColaborador
from competencias.models.competencia import Competencia


class ColaboradorNoFijaEstadoDeFinalizacionDirectamenteTests(CapacitacionTestBase):
    """T028: un colaborador no puede fijar directamente `completado_at`, la
    calificación final (`ResultadoEvaluacion.correctas`/`.total`) ni el
    nivel de competencia de su propia inscripción vía la API (AC10)."""

    def setUp(self):
        self.client = APIClient()
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

    def test_colaborador_no_puede_fijar_completado_at_por_patch(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.patch(
            f'/api/capacitacion/mis-inscripciones/{self.inscripcion.id}/',
            {'completado_at': '2026-01-02T00:00:00Z'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.inscripcion.refresh_from_db()
        self.assertIsNone(self.inscripcion.completado_at)

    def test_colaborador_no_puede_fijar_nivel_de_competencia(self):
        nivel_2 = NivelCompetencia.objects.create(nombre='Nivel 2', codigo='nivel-2', orden=2)
        nivel_3 = NivelCompetencia.objects.create(nombre='Nivel 3', codigo='nivel-3', orden=3)
        competencia = Competencia.objects.create(nombre='Competencia X', codigo='competencia-x')
        registro = CompetenciaColaborador.objects.create(
            colaborador=self.colaborador, competencia=competencia, nivel=nivel_2,
        )

        self.client.force_authenticate(self.colaborador)
        resp = self.client.patch(
            f'/api/competencias/competencias-colaborador/{registro.id}/',
            {'nivel': nivel_3.id},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)
        registro.refresh_from_db()
        self.assertEqual(registro.nivel, nivel_2)
