from datetime import date

from rest_framework.test import APIClient

from capacitacion.models import Inscripcion, Periodo
from capacitacion.tests.base import CapacitacionTestBase
from catalogos.models import NivelCompetencia
from competencias.models.competencia import Competencia
from competencias.models.ruta import RutaAprendizaje, RutaAprendizajeCurso


class MiInscripcionRutaPerfilTests(CapacitacionTestBase):
    """T035: MiInscripcionRutaPerfil auto-inscribe en el periodo abierto más
    reciente del curso vía InscripcionService, y falla explícitamente si no
    hay ninguno abierto — nunca crea un periodo por su cuenta (AC18)."""

    def setUp(self):
        self.client = APIClient()
        nivel = NivelCompetencia.objects.create(nombre='Nivel 1', codigo='nivel-1', orden=1)
        competencia = Competencia.objects.create(nombre='Competencia X', codigo='competencia-x')
        self.ruta = RutaAprendizaje.objects.create(nombre='Ruta X', competencia=competencia, nivel_objetivo=nivel)
        RutaAprendizajeCurso.objects.create(ruta=self.ruta, curso=self.curso_a, orden=1)

    def test_autoinscribe_en_el_periodo_abierto_mas_reciente(self):
        Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        periodo_reciente = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 2', fecha_inicio=date(2026, 2, 1),
        )

        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/competencias/iniciar-ruta/', {'ruta_id': self.ruta.id}, format='json')

        self.assertEqual(resp.status_code, 201)
        inscripcion = Inscripcion.objects.get(pk=resp.data['inscripcion_id'])
        self.assertEqual(inscripcion.periodo_id, periodo_reciente.id)

    def test_falla_explicitamente_si_no_hay_periodo_abierto_sin_crear_uno(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/competencias/iniciar-ruta/', {'ruta_id': self.ruta.id}, format='json')

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Inscripcion.objects.filter(colaborador=self.colaborador, curso=self.curso_a).exists())
        self.assertFalse(Periodo.objects.filter(curso=self.curso_a).exists())
