from rest_framework.test import APIClient

from capacitacion.models import ContenidoBloque
from capacitacion.tests.base import CapacitacionTestBase


class BloqueEmbedUrlTests(CapacitacionTestBase):
    """ContenidoBloque.embed_url permite insertar un enlace de embed (Canva
    'Insertar en un sitio web', o cualquier otro iframe-embed) como su propio
    campo, separado de video_url/imagen_url — el frontend lo renderiza en un
    <iframe> en vez de un <video>/<img>."""

    def test_admin_puede_crear_bloque_con_embed_url(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin_a)
        payload = {
            'tema': self.tema_a.id,
            'tipo': self.tipo_texto.id,
            'orden': 1,
            'embed_url': 'https://www.canva.com/design/ABC123/view?embed',
        }
        resp = self.client.post('/api/capacitacion/bloques/', payload, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['embed_url'], 'https://www.canva.com/design/ABC123/view?embed')

    def test_colaborador_ve_el_embed_url_del_bloque(self):
        bloque = ContenidoBloque.objects.create(
            tema=self.tema_a, tipo=self.tipo_texto, orden=1,
            embed_url='https://www.canva.com/design/ABC123/view?embed',
        )

        self.client = APIClient()
        self.client.force_authenticate(self.colaborador)
        resp = self.client.get(f'/api/capacitacion/ver/bloques/?tema={self.tema_a.id}')
        self.assertEqual(resp.status_code, 200)

        bloque_data = next(b for b in resp.data['results'] if b['id'] == bloque.id)
        self.assertEqual(bloque_data['embed_url'], 'https://www.canva.com/design/ABC123/view?embed')

    def test_embed_url_vacio_por_default(self):
        bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_texto, orden=1)
        self.assertEqual(bloque.embed_url, '')

    def test_link_real_de_canva_enviado_por_el_usuario(self):
        """Link real proporcionado por el usuario: enlace de 'Compartir' de
        Canva (termina en /view, sin ?embed) — se guarda y se lee igual,
        porque embed_url es texto libre sin validación de dominio/formato."""
        url_canva = 'https://www.canva.com/design/DAHacbppHVY/ZidskV_or85sqe0GgoMNsQ/view'
        self.client = APIClient()
        self.client.force_authenticate(self.admin_a)
        payload = {
            'tema': self.tema_a.id, 'tipo': self.tipo_texto.id, 'orden': 1,
            'embed_url': url_canva,
        }
        resp = self.client.post('/api/capacitacion/bloques/', payload, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['embed_url'], url_canva)

        self.client.force_authenticate(self.colaborador)
        get_resp = self.client.get(f'/api/capacitacion/ver/bloques/?tema={self.tema_a.id}')
        self.assertEqual(get_resp.status_code, 200)
        bloque_data = next(b for b in get_resp.data['results'] if b['id'] == resp.data['id'])
        self.assertEqual(bloque_data['embed_url'], url_canva)
