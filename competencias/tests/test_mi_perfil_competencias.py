from datetime import date

from django.utils import timezone
from rest_framework.test import APIClient

from catalogos.models import NivelCompetencia
from capacitacion.models import Inscripcion, Periodo
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase
from competencias.models.competencia import Competencia, CompetenciaPuesto
from competencias.models.ruta import RutaAprendizaje, RutaAprendizajeCurso


class MiPerfilCompetenciasDosInscripcionesTests(CapacitacionTestBase):
    """T033: MiPerfilCompetenciasView muestra la inscripción más reciente
    por curso cuando hay dos — hoy colapsa por orden de iteración del dict
    (la ruta de aprendizaje reporta el estado de la inscripción incorrecta)."""

    def setUp(self):
        self.client = APIClient()
        self.colaborador.puesto = self.puesto
        self.colaborador.save(update_fields=['puesto'])

        nivel = NivelCompetencia.objects.create(nombre='Nivel 1', codigo='nivel-1', orden=1)
        competencia = Competencia.objects.create(nombre='Competencia X', codigo='competencia-x')
        CompetenciaPuesto.objects.create(puesto=self.puesto, competencia=competencia, nivel=nivel)

        ruta = RutaAprendizaje.objects.create(nombre='Ruta X', competencia=competencia, nivel_objetivo=nivel)
        RutaAprendizajeCurso.objects.create(ruta=ruta, curso=self.curso_a, orden=1)

        periodo_1 = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion_1 = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo_1)
        self.assertIsInstance(inscripcion_1, Inscripcion)
        inscripcion_1.completado_at = timezone.now()
        inscripcion_1.save(update_fields=['completado_at'])

        periodo_2 = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 2', fecha_inicio=date(2026, 2, 1),
        )
        self.inscripcion_2 = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo_2)
        self.assertIsInstance(self.inscripcion_2, Inscripcion)
        self.assertIsNone(self.inscripcion_2.completado_at)

    def test_reporta_el_estado_de_la_inscripcion_mas_reciente_no_la_mas_antigua(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.get('/api/competencias/mi-perfil/')
        self.assertEqual(resp.status_code, 200)

        ruta_data = resp.data[0]['rutas_recomendadas'][0]
        curso_data = ruta_data['cursos'][0]
        self.assertEqual(curso_data['inscripcion_id'], self.inscripcion_2.id)
        self.assertFalse(curso_data['completado'])
