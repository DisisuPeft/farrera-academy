from datetime import date

from rest_framework.test import APIClient

from capacitacion.models import ContenidoBloque, ContenidoBloqueOpcion, ContenidoBloqueRespuesta, Periodo
from capacitacion.services.inscripcion_service import InscripcionService
from .base import CapacitacionTestBase


class MisRespuestasBloqueTests(CapacitacionTestBase):
    def setUp(self):
        self.client = APIClient()
        self.bloque = ContenidoBloque.objects.create(
            tema=self.tema_a, tipo=self.tipo_opcion_multiple, orden=1, texto='¿2+2?',
        )
        self.op_correcta = ContenidoBloqueOpcion.objects.create(
            bloque=self.bloque, orden=1, texto='4', es_correcta=True,
        )
        self.op_incorrecta = ContenidoBloqueOpcion.objects.create(
            bloque=self.bloque, orden=2, texto='5', es_correcta=False,
        )
        periodo = Periodo.objects.create(curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1))
        self.inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=periodo)

    def test_responder_correctamente_queda_marcado_como_correcto(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/mis-respuestas-bloque/', {
            'bloque': self.bloque.id, 'opcion_seleccionada': self.op_correcta.id,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data['es_correcta'])

    def test_responder_incorrectamente_queda_marcado_como_incorrecto(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/mis-respuestas-bloque/', {
            'bloque': self.bloque.id, 'opcion_seleccionada': self.op_incorrecta.id,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.data['es_correcta'])

    def test_es_correcta_no_se_puede_forzar_desde_el_cliente(self):
        """Aunque el cliente mande es_correcta=True en el payload para una
        opción incorrecta, el servidor recalcula y lo ignora (read_only)."""
        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/mis-respuestas-bloque/', {
            'bloque': self.bloque.id, 'opcion_seleccionada': self.op_incorrecta.id,
            'es_correcta': True,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.data['es_correcta'])
        respuesta = ContenidoBloqueRespuesta.objects.get(id=resp.data['id'])
        self.assertFalse(respuesta.es_correcta)

    def test_rechaza_opcion_que_no_pertenece_al_bloque(self):
        otro_bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_opcion_multiple, orden=2)
        opcion_ajena = ContenidoBloqueOpcion.objects.create(bloque=otro_bloque, orden=1, texto='X', es_correcta=True)

        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/mis-respuestas-bloque/', {
            'bloque': self.bloque.id, 'opcion_seleccionada': opcion_ajena.id,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('opcion_seleccionada', resp.data)

    def test_colaborador_solo_ve_sus_propias_respuestas(self):
        from .base import hacer_usuario
        otro_colaborador = hacer_usuario(self.dependencia_a)
        otro_periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 2', fecha_inicio=date(2026, 2, 1),
        )
        otra_inscripcion = InscripcionService.crear(colaborador=otro_colaborador, periodo=otro_periodo)

        ContenidoBloqueRespuesta.objects.create(
            inscripcion=self.inscripcion, bloque=self.bloque,
            opcion_seleccionada=self.op_correcta, es_correcta=True,
        )
        ContenidoBloqueRespuesta.objects.create(
            inscripcion=otra_inscripcion, bloque=self.bloque,
            opcion_seleccionada=self.op_incorrecta, es_correcta=False,
        )

        self.client.force_authenticate(self.colaborador)
        resp = self.client.get('/api/capacitacion/mis-respuestas-bloque/')
        self.assertEqual(resp.data['count'], 1)

    def test_no_se_puede_editar_una_respuesta_ya_enviada(self):
        respuesta = ContenidoBloqueRespuesta.objects.create(
            inscripcion=self.inscripcion, bloque=self.bloque,
            opcion_seleccionada=self.op_incorrecta, es_correcta=False,
        )
        self.client.force_authenticate(self.colaborador)
        resp = self.client.patch(f'/api/capacitacion/mis-respuestas-bloque/{respuesta.id}/', {
            'opcion_seleccionada': self.op_correcta.id,
        }, format='json')
        self.assertEqual(resp.status_code, 405)


class ContenidoBloqueOpcionAdminTests(CapacitacionTestBase):
    """CRUD de autoría de opciones — solo Administrador, incluye es_correcta."""

    def setUp(self):
        self.client = APIClient()
        self.bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_opcion_multiple, orden=1)

    def test_admin_crea_opcion_con_es_correcta(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.post('/api/capacitacion/bloque-opciones/', {
            'bloque': self.bloque.id, 'orden': 1, 'texto': 'Verdadero', 'es_correcta': True,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data['es_correcta'])

    def test_colaborador_no_puede_crear_opciones(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/bloque-opciones/', {
            'bloque': self.bloque.id, 'orden': 1, 'texto': 'X', 'es_correcta': True,
        }, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_borrar_opcion_cierra_el_hueco_de_orden(self):
        op1 = ContenidoBloqueOpcion.objects.create(bloque=self.bloque, orden=1, texto='A')
        op2 = ContenidoBloqueOpcion.objects.create(bloque=self.bloque, orden=2, texto='B')
        op3 = ContenidoBloqueOpcion.objects.create(bloque=self.bloque, orden=3, texto='C')

        self.client.force_authenticate(self.admin_a)
        resp = self.client.delete(f'/api/capacitacion/bloque-opciones/{op1.id}/')
        self.assertEqual(resp.status_code, 204)

        op2.refresh_from_db()
        op3.refresh_from_db()
        self.assertEqual((op2.orden, op3.orden), (1, 2))
