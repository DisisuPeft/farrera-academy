from rest_framework.test import APIClient

from capacitacion.models import ContenidoBloque, ContenidoBloqueItem, ContenidoBloqueOpcion
from capacitacion.serializers import ContenidoBloqueSerializer
from capacitacion.serializers.colaborador import ContenidoBloqueColaboradorSerializer
from .base import CapacitacionTestBase


class ContenidoBloqueSerializerTests(CapacitacionTestBase):
    """tipo_codigo + ítems/archivos/opciones anidados (admin)."""

    def test_tipo_codigo_expone_el_codigo_estable_no_el_nombre(self):
        bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_texto, orden=1)
        data = ContenidoBloqueSerializer(bloque).data
        self.assertEqual(data['tipo_codigo'], 'texto-imagen-test')
        self.assertEqual(data['tipo_nombre'], 'Texto con imagen')

    def test_bloque_items_anidados_en_orden(self):
        bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_texto, orden=1)
        ContenidoBloqueItem.objects.create(bloque=bloque, orden=2, titulo='segundo')
        ContenidoBloqueItem.objects.create(bloque=bloque, orden=1, titulo='primero')

        data = ContenidoBloqueSerializer(bloque).data
        titulos = [item['titulo'] for item in data['bloque_items']]
        self.assertEqual(titulos, ['primero', 'segundo'])

    def test_admin_serializer_incluye_es_correcta_en_opciones(self):
        bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_opcion_multiple, orden=1)
        ContenidoBloqueOpcion.objects.create(bloque=bloque, orden=1, texto='A', es_correcta=True)

        data = ContenidoBloqueSerializer(bloque).data
        self.assertIn('es_correcta', data['opciones'][0])
        self.assertTrue(data['opciones'][0]['es_correcta'])


class ContenidoBloqueColaboradorSerializerTests(CapacitacionTestBase):
    """El colaborador nunca debe ver `es_correcta` de una opción."""

    def test_colaborador_serializer_excluye_es_correcta(self):
        bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_opcion_multiple, orden=1)
        ContenidoBloqueOpcion.objects.create(bloque=bloque, orden=1, texto='A', es_correcta=True)
        ContenidoBloqueOpcion.objects.create(bloque=bloque, orden=2, texto='B', es_correcta=False)

        data = ContenidoBloqueColaboradorSerializer(bloque, context={'request': None}).data
        self.assertEqual(len(data['opciones']), 2)
        for opcion in data['opciones']:
            self.assertNotIn('es_correcta', opcion)

    def test_colaborador_serializer_expone_tipo_codigo(self):
        bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_texto, orden=1)
        data = ContenidoBloqueColaboradorSerializer(bloque, context={'request': None}).data
        self.assertEqual(data['tipo_codigo'], 'texto-imagen-test')


class ContenidoBloqueEndpointTests(CapacitacionTestBase):
    """CRUD básico de /bloques/ y /bloque-items/ a través de la API, con permisos."""

    def setUp(self):
        self.client = APIClient()

    def test_colaborador_no_puede_crear_bloques(self):
        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/bloques/', {
            'tema': self.tema_a.id, 'tipo': self.tipo_texto.id, 'orden': 1,
        }, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_admin_puede_crear_y_listar_bloques(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.post('/api/capacitacion/bloques/', {
            'tema': self.tema_a.id, 'tipo': self.tipo_texto.id, 'orden': 1, 'texto': 'hola',
        }, format='json')
        self.assertEqual(resp.status_code, 201)

        resp = self.client.get('/api/capacitacion/bloques/?pagination=false')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_endpoint_sin_autenticacion_devuelve_401(self):
        resp = self.client.get('/api/capacitacion/bloques/')
        self.assertEqual(resp.status_code, 401)
