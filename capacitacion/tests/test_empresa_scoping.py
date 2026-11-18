from datetime import date

from rest_framework.test import APIClient

from capacitacion.models import ContenidoBloque, Inscripcion, Modulo, Periodo, Tema
from capacitacion.services.inscripcion_service import InscripcionService
from .base import CapacitacionTestBase


class CursoScopingTests(CapacitacionTestBase):
    """Ámbito de autorización: un Administrador no-superuser solo ve/edita los
    cursos de su propia empresa, más los globales (empresa=None)."""

    def setUp(self):
        self.client = APIClient()

    def test_admin_de_empresa_b_no_ve_curso_de_empresa_a(self):
        self.client.force_authenticate(self.admin_b)
        resp = self.client.get('/api/capacitacion/cursos/?pagination=false')
        ids = [c['id'] for c in resp.data]
        self.assertNotIn(self.curso_a.id, ids)

    def test_admin_de_empresa_a_si_ve_su_curso(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.get('/api/capacitacion/cursos/?pagination=false')
        ids = [c['id'] for c in resp.data]
        self.assertIn(self.curso_a.id, ids)

    def test_superuser_ve_cursos_de_todas_las_empresas(self):
        self.client.force_authenticate(self.superuser)
        resp = self.client.get('/api/capacitacion/cursos/?pagination=false')
        ids = [c['id'] for c in resp.data]
        self.assertIn(self.curso_a.id, ids)

    def test_curso_global_sin_empresa_es_visible_para_cualquier_admin(self):
        from capacitacion.models import Curso
        curso_global = Curso.objects.create(titulo='Curso global', status=self.status_publicado, empresa=None)

        self.client.force_authenticate(self.admin_b)
        resp = self.client.get('/api/capacitacion/cursos/?pagination=false')
        ids = [c['id'] for c in resp.data]
        self.assertIn(curso_global.id, ids)

    def test_admin_no_puede_editar_curso_de_otra_empresa(self):
        self.client.force_authenticate(self.admin_b)
        resp = self.client.patch(f'/api/capacitacion/cursos/{self.curso_a.id}/', {'titulo': 'hackeado'}, format='json')
        self.assertEqual(resp.status_code, 404)  # no 403: ni siquiera debe saber que existe
        self.curso_a.refresh_from_db()
        self.assertEqual(self.curso_a.titulo, 'Curso de A')

    def test_al_crear_un_curso_se_asigna_automaticamente_la_empresa_del_usuario(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.post('/api/capacitacion/cursos/', {
            'titulo': 'Nuevo curso', 'status': self.status_publicado.id,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['empresa'], self.empresa_a.id)

    def test_un_admin_no_puede_forzar_otra_empresa_al_crear(self):
        """Aunque mande `empresa` en el payload, el backend lo ignora y usa la
        empresa real del usuario (no se puede escalar privilegios)."""
        self.client.force_authenticate(self.admin_a)
        resp = self.client.post('/api/capacitacion/cursos/', {
            'titulo': 'Intento de escalar', 'status': self.status_publicado.id,
            'empresa': self.empresa_b.id,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['empresa'], self.empresa_a.id)

    def test_creado_por_se_asigna_automaticamente(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.post('/api/capacitacion/cursos/', {
            'titulo': 'Curso con dueño', 'status': self.status_publicado.id,
        }, format='json')
        self.assertEqual(resp.data['creado_por'], self.admin_a.id)


class ScopingEnCascadaTests(CapacitacionTestBase):
    """El ámbito por empresa se propaga a Módulo/Tema/Bloque, no solo a Curso."""

    def setUp(self):
        self.client = APIClient()
        self.modulo = Modulo.objects.create(curso=self.curso_a, titulo='Mod', orden=2)
        self.tema = Tema.objects.create(modulo=self.modulo, titulo='T', tipo=self.tipo_tema, orden=1)
        self.bloque = ContenidoBloque.objects.create(tema=self.tema, tipo=self.tipo_texto, orden=1)

    def test_admin_de_otra_empresa_no_ve_modulos_del_curso_ajeno(self):
        self.client.force_authenticate(self.admin_b)
        resp = self.client.get(f'/api/capacitacion/modulos/?curso={self.curso_a.id}&pagination=false')
        self.assertEqual(resp.data, [])

    def test_admin_de_otra_empresa_no_ve_bloques_del_curso_ajeno(self):
        self.client.force_authenticate(self.admin_b)
        resp = self.client.get(f'/api/capacitacion/bloques/?tema={self.tema.id}&pagination=false')
        self.assertEqual(resp.data, [])

    def test_admin_de_otra_empresa_no_puede_borrar_bloque_ajeno(self):
        self.client.force_authenticate(self.admin_b)
        resp = self.client.delete(f'/api/capacitacion/bloques/{self.bloque.id}/')
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(ContenidoBloque.objects.filter(id=self.bloque.id).exists())


class InscripcionScopingTests(CapacitacionTestBase):
    """Cierre (closing review): InscripcionViewSet/ProgresoTemaViewSet/
    ResultadoEvaluacionViewSet nunca aplicaban `_scope_por_empresa`, a
    diferencia de sus hermanos (CursoViewSet/ModuloViewSet/...) agregados en
    el mismo cambio — un Administrador de OTRA empresa podía ver, y forzar la
    finalización/acreditación de, la inscripción de un colaborador ajeno."""

    def setUp(self):
        self.client = APIClient()
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

    def test_admin_de_otra_empresa_no_ve_inscripcion_ajena_en_el_listado(self):
        self.client.force_authenticate(self.admin_b)
        resp = self.client.get('/api/capacitacion/inscripciones/?pagination=false')
        self.assertEqual(resp.status_code, 200)
        ids = [row['id'] for row in resp.data]
        self.assertNotIn(self.inscripcion.id, ids)

    def test_admin_de_otra_empresa_no_puede_forzar_inscripcion_ajena(self):
        self.client.force_authenticate(self.admin_b)
        resp = self.client.post(f'/api/capacitacion/inscripciones/{self.inscripcion.id}/forzar/')
        self.assertEqual(resp.status_code, 404)
        self.inscripcion.refresh_from_db()
        self.assertIsNone(self.inscripcion.completado_at)

    def test_admin_de_su_propia_empresa_si_puede_forzar(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.post(f'/api/capacitacion/inscripciones/{self.inscripcion.id}/forzar/')
        self.assertEqual(resp.status_code, 200)

    def test_admin_de_otra_empresa_no_ve_progreso_tema_ajeno(self):
        from capacitacion.models import ProgresoTema
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)

        self.client.force_authenticate(self.admin_b)
        resp = self.client.get('/api/capacitacion/progresos-tema/?pagination=false')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])

    def test_admin_de_otra_empresa_no_ve_resultado_evaluacion_ajeno(self):
        from catalogos.models import TipoEvaluacion
        from capacitacion.models import Evaluacion, ResultadoEvaluacion
        tipo_evaluacion = TipoEvaluacion.objects.create(nombre='Módulo', codigo='modulo-test-scoping')
        evaluacion = Evaluacion.objects.create(titulo='Eval 1', tipo=tipo_evaluacion, modulo=self.modulo_a)
        ResultadoEvaluacion.objects.create(inscripcion=self.inscripcion, evaluacion=evaluacion, correctas=1, total=1)

        self.client.force_authenticate(self.admin_b)
        resp = self.client.get('/api/capacitacion/resultados-evaluacion/?pagination=false')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])


class InscripcionCamposDeSoloLecturaAdminTests(CapacitacionTestBase):
    """Cierre (closing review): el serializer admin de Inscripcion dejaba
    `completado_at` y `curso` escribibles directamente por PATCH — un
    Administrador podía auto-finalizar sin pasar por FinalizacionService
    (contradice la Clarification #3 de la spec: 'nunca editando completado_at
    u otro campo de estado directamente'), y podía divergir `curso` de
    `periodo.curso` sin ningún chequeo."""

    def setUp(self):
        self.client = APIClient()
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

        self.otro_curso = type(self.curso_a).objects.create(
            titulo='Otro curso', status=self.status_publicado, empresa=self.empresa_a,
        )

    def test_admin_no_puede_fijar_completado_at_directamente(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.patch(
            f'/api/capacitacion/inscripciones/{self.inscripcion.id}/',
            {'completado_at': '2026-01-01T00:00:00Z'},
            format='json',
        )
        self.assertIn(resp.status_code, (200, 400))

        self.inscripcion.refresh_from_db()
        self.assertIsNone(self.inscripcion.completado_at)

    def test_admin_no_puede_divergir_curso_del_periodo(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.patch(
            f'/api/capacitacion/inscripciones/{self.inscripcion.id}/',
            {'curso': self.otro_curso.id},
            format='json',
        )
        self.assertIn(resp.status_code, (200, 400))

        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.curso_id, self.periodo.curso_id)
        self.assertNotEqual(self.inscripcion.curso_id, self.otro_curso.id)
