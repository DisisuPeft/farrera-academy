from datetime import date

from rest_framework.test import APIClient

from catalogos.models import TipoEvaluacion
from capacitacion.models import (
    Curso, Evaluacion, Inscripcion, Modulo, Periodo, Pregunta, OpcionPregunta,
    ProgresoTema, ResultadoEvaluacion, Tema,
)
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase


class ReconexionMisInscripcionesTests(CapacitacionTestBase):
    """T032: /mis-inscripciones/ crea vía InscripcionService, no por creación
    directa de modelo (AC1)."""

    def setUp(self):
        self.client = APIClient()
        Periodo.objects.create(curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1))

    def test_colaborador_se_autoinscribe_a_un_curso_con_periodo_abierto(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/mis-inscripciones/', {'curso': self.curso_a.id}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(Inscripcion.objects.filter(colaborador=self.colaborador, curso=self.curso_a).exists())

    def test_rechaza_inscripcion_a_curso_sin_periodo_abierto(self):
        curso_sin_periodo = self.curso_a
        Periodo.objects.filter(curso=curso_sin_periodo).update(estado=Periodo.Estado.CERRADO)

        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/mis-inscripciones/', {'curso': curso_sin_periodo.id}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_rechaza_doble_inscripcion_al_mismo_periodo(self):
        self.client.force_authenticate(self.colaborador)
        self.client.post('/api/capacitacion/mis-inscripciones/', {'curso': self.curso_a.id}, format='json')

        resp = self.client.post('/api/capacitacion/mis-inscripciones/', {'curso': self.curso_a.id}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Inscripcion.objects.filter(colaborador=self.colaborador, curso=self.curso_a).count(), 1)


class ReconexionMisProgresosYResultadosTests(CapacitacionTestBase):
    """T032: /mis-progresos/ y /mis-resultados/ crean vía EvidenciaService,
    con validación cruzada contra la inscripción activa (AC2, AC8)."""

    def setUp(self):
        self.client = APIClient()
        periodo = Periodo.objects.create(curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1))
        self.inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo)
        self.assertIsInstance(self.inscripcion, Inscripcion)

    def test_registrar_progreso_de_un_tema_del_curso_inscrito(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/mis-progresos/', {'tema': self.tema_a.id}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(ProgresoTema.objects.filter(inscripcion=self.inscripcion, tema=self.tema_a).exists())

    def test_rechaza_progreso_de_un_tema_ajeno_al_curso_inscrito(self):
        otro_curso = Curso.objects.create(
            titulo='Otro curso', status=self.status_publicado, empresa=self.empresa_a,
        )
        otro_modulo = Modulo.objects.create(curso=otro_curso, titulo='M', orden=1)
        otro_tema = Tema.objects.create(modulo=otro_modulo, titulo='T', tipo=self.tipo_tema, orden=1)

        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/mis-progresos/', {'tema': otro_tema.id}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_registrar_resultado_de_evaluacion_del_curso_inscrito(self):
        tipo_evaluacion = TipoEvaluacion.objects.create(nombre='Módulo', codigo='modulo-test')
        evaluacion = Evaluacion.objects.create(titulo='Eval 1', tipo=tipo_evaluacion, modulo=self.modulo_a)
        pregunta = Pregunta.objects.create(evaluacion=evaluacion, texto='¿?', orden=1)
        opcion_correcta = OpcionPregunta.objects.create(pregunta=pregunta, texto='Sí', orden=1, es_correcta=True)

        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/mis-resultados/', {
            'evaluacion': evaluacion.id,
            'respuestas': [{'pregunta': pregunta.id, 'opcion': opcion_correcta.id}],
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['correctas'], 1)
        self.assertEqual(resp.data['total'], 1)
        self.assertTrue(ResultadoEvaluacion.objects.filter(inscripcion=self.inscripcion, evaluacion=evaluacion).exists())


class ReconexionGetInscritoYProgresoTests(CapacitacionTestBase):
    """T032: get_inscrito/get_progreso (CursoColaboradorSerializer,
    ModuloColaboradorSerializer) ya no crashean al consultar
    ProgresoTema/ResultadoEvaluacion por `inscripcion__colaborador` en vez
    del `colaborador` directo eliminado en T009/T010."""

    def setUp(self):
        self.client = APIClient()
        periodo = Periodo.objects.create(curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1))
        self.inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo)
        self.assertIsInstance(self.inscripcion, Inscripcion)
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)

    def test_ver_cursos_no_crashea_y_refleja_inscripcion_y_progreso(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.get('/api/capacitacion/ver/cursos/')
        self.assertEqual(resp.status_code, 200)
        curso_data = next(c for c in resp.data['results'] if c['id'] == self.curso_a.id)
        self.assertTrue(curso_data['inscrito'])
        self.assertEqual(curso_data['progreso']['completados'], 1)

    def test_mis_cursos_no_crashea(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.get('/api/capacitacion/mis-cursos/')
        self.assertEqual(resp.status_code, 200)

    def test_ver_modulos_no_crashea_y_refleja_progreso(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.get(f'/api/capacitacion/ver/modulos/?curso={self.curso_a.id}')
        self.assertEqual(resp.status_code, 200)
        modulo_data = next(m for m in resp.data['results'] if m['id'] == self.modulo_a.id)
        self.assertEqual(modulo_data['progreso']['completados'], 1)
