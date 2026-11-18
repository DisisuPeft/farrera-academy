from django.test import TestCase
from rest_framework.test import APIClient

from catalogos.models import TipoBloqueContenido
from catalogos.models.capacitacion import CategoriaPedagogica
from catalogos.serializers import TipoBloqueContenidoSerializer


class TipoBloqueContenidoExtensibilidadTests(TestCase):
    """El catálogo de tipos de bloque es extensible: categoría pedagógica,
    config de campos, JSON Schema de validación, capacidades y versión."""

    def test_defaults_de_un_tipo_nuevo(self):
        tipo = TipoBloqueContenido.objects.create(nombre='Prueba', codigo='prueba-test')
        self.assertEqual(tipo.categoria, CategoriaPedagogica.CONTENIDO)
        self.assertEqual(tipo.version_esquema, 1)
        self.assertIsNone(tipo.config)
        self.assertIsNone(tipo.capacidades)

    def test_categoria_acepta_las_6_categorias_del_prompt(self):
        for categoria, _ in CategoriaPedagogica.choices:
            tipo = TipoBloqueContenido.objects.create(nombre=categoria, codigo=f'cat-{categoria}', categoria=categoria)
            tipo.full_clean()  # valida que el choice sea aceptado

    def test_serializer_expone_los_campos_de_configuracion(self):
        tipo = TipoBloqueContenido.objects.create(
            nombre='Acordeón', codigo='acordeon-test',
            categoria=CategoriaPedagogica.EXPLORACION,
            config={'campos': ['texto'], 'items': 'bloque_items'},
            capacidades=['soporta_items', 'colapsable'],
        )
        data = TipoBloqueContenidoSerializer(tipo).data
        self.assertEqual(data['categoria'], 'exploracion')
        self.assertEqual(data['config'], {'campos': ['texto'], 'items': 'bloque_items'})
        self.assertEqual(data['capacidades'], ['soporta_items', 'colapsable'])


class CatalogoPaginacionDinamicaTests(TestCase):
    """Los catálogos deben poder consultarse sin paginar via ?pagination=false
    (requisito explícito del prompt para selects del frontend)."""

    def setUp(self):
        self.client = APIClient()
        # reutiliza el helper de creación de usuario sin heredar todo el fixture pesado
        from capacitacion.tests.base import hacer_usuario
        from sistema.models import Empresa, Dependencia

        empresa = Empresa.objects.create(razon_social='E', slug='e-pag-test')
        dependencia = Dependencia.objects.create(nombre='D', empresa=empresa)
        self.user = hacer_usuario(dependencia, es_superuser=True)

        for i in range(15):
            TipoBloqueContenido.objects.create(nombre=f'Tipo {i}', codigo=f'tipo-pag-{i}')

    def test_sin_query_param_devuelve_paginado(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get('/api/catalogos/tipos-bloque/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('results', resp.data)
        self.assertIn('count', resp.data)
        self.assertLess(len(resp.data['results']), 15)

    def test_con_pagination_false_devuelve_todo(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get('/api/catalogos/tipos-bloque/?pagination=false')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIsInstance(resp.data, dict)
        self.assertEqual(len(resp.data), 15)
