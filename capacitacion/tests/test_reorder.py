from rest_framework.test import APIClient

from capacitacion.models import ContenidoBloque, ContenidoBloqueItem, ContenidoBloqueOpcion
from .base import CapacitacionTestBase


class ReordenarBloquesTests(CapacitacionTestBase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin_a)
        self.bloques = [
            ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_texto, orden=i, texto=f'b{i}')
            for i in range(1, 4)
        ]

    def test_reordenar_en_lote_aplica_el_nuevo_orden(self):
        b1, b2, b3 = self.bloques
        payload = {'tema': self.tema_a.id, 'orden': [
            {'id': b1.id, 'orden': 3}, {'id': b2.id, 'orden': 1}, {'id': b3.id, 'orden': 2},
        ]}
        resp = self.client.patch('/api/capacitacion/bloques/reordenar/', payload, format='json')
        self.assertEqual(resp.status_code, 200)

        b1.refresh_from_db()
        b2.refresh_from_db()
        b3.refresh_from_db()
        self.assertEqual((b1.orden, b2.orden, b3.orden), (3, 1, 2))

    def test_reordenar_rechaza_ids_repetidos(self):
        b1, b2, _ = self.bloques
        payload = {'tema': self.tema_a.id, 'orden': [
            {'id': b1.id, 'orden': 1}, {'id': b1.id, 'orden': 2},
        ]}
        resp = self.client.patch('/api/capacitacion/bloques/reordenar/', payload, format='json')
        self.assertEqual(resp.status_code, 400)
        b1.refresh_from_db()
        b2.refresh_from_db()
        self.assertEqual(b1.orden, 1)  # nada se tocó

    def test_reordenar_rechaza_ordenes_repetidos(self):
        b1, b2, _ = self.bloques
        payload = {'tema': self.tema_a.id, 'orden': [
            {'id': b1.id, 'orden': 5}, {'id': b2.id, 'orden': 5},
        ]}
        resp = self.client.patch('/api/capacitacion/bloques/reordenar/', payload, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_reordenar_rechaza_bloque_de_otro_tema(self):
        from capacitacion.models import Modulo, Tema
        otro_modulo = Modulo.objects.create(curso=self.curso_a, titulo='Otro módulo', orden=2)
        otro_tema = Tema.objects.create(modulo=otro_modulo, titulo='Otro tema', tipo=self.tipo_tema, orden=1)
        bloque_ajeno = ContenidoBloque.objects.create(tema=otro_tema, tipo=self.tipo_texto, orden=1)

        payload = {'tema': self.tema_a.id, 'orden': [{'id': bloque_ajeno.id, 'orden': 1}]}
        resp = self.client.patch('/api/capacitacion/bloques/reordenar/', payload, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_reordenar_no_rompe_el_unique_together_con_valores_intermedios(self):
        """El paso intermedio usado para esquivar unique_together(tema, orden) no
        debe dejar basura ni fallar aunque se invierta todo el orden."""
        b1, b2, b3 = self.bloques
        payload = {'tema': self.tema_a.id, 'orden': [
            {'id': b1.id, 'orden': 1}, {'id': b2.id, 'orden': 2}, {'id': b3.id, 'orden': 3},
        ]}
        resp = self.client.patch('/api/capacitacion/bloques/reordenar/', payload, format='json')
        self.assertEqual(resp.status_code, 200)
        ordenes = list(
            ContenidoBloque.objects.filter(tema=self.tema_a).order_by('orden').values_list('orden', flat=True)
        )
        self.assertEqual(ordenes, [1, 2, 3])


class ReordenarItemsYOpcionesTests(CapacitacionTestBase):
    """El mismo `_reordenar_en_lote` se reutiliza para bloque-items, bloque-archivos
    y bloque-opciones; basta probarlo una vez más en items y opciones."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin_a)
        self.bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_texto, orden=1)

    def test_reordenar_items(self):
        items = [
            ContenidoBloqueItem.objects.create(bloque=self.bloque, orden=i, titulo=f'item{i}')
            for i in range(1, 4)
        ]
        payload = {'bloque': self.bloque.id, 'orden': [
            {'id': items[0].id, 'orden': 3}, {'id': items[1].id, 'orden': 1}, {'id': items[2].id, 'orden': 2},
        ]}
        resp = self.client.patch('/api/capacitacion/bloque-items/reordenar/', payload, format='json')
        self.assertEqual(resp.status_code, 200)
        items[0].refresh_from_db()
        self.assertEqual(items[0].orden, 3)

    def test_reordenar_opciones(self):
        bloque_om = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_opcion_multiple, orden=2)
        op1 = ContenidoBloqueOpcion.objects.create(bloque=bloque_om, orden=1, texto='A')
        op2 = ContenidoBloqueOpcion.objects.create(bloque=bloque_om, orden=2, texto='B')

        payload = {'bloque': bloque_om.id, 'orden': [{'id': op1.id, 'orden': 2}, {'id': op2.id, 'orden': 1}]}
        resp = self.client.patch('/api/capacitacion/bloque-opciones/reordenar/', payload, format='json')
        self.assertEqual(resp.status_code, 200)
        op1.refresh_from_db()
        op2.refresh_from_db()
        self.assertEqual((op1.orden, op2.orden), (2, 1))
