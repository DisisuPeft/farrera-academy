import base64

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from capacitacion.models import ContenidoBloque, ContenidoBloqueArchivo
from capacitacion.tests.base import CapacitacionTestBase

# PNG 1x1 real (Pillow valida contenido, no solo content_type/extensión).
_PNG_1X1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)


class UrlsDeArchivosUsanGatewayProtegidoTests(CapacitacionTestBase):
    """Las URLs de imagen_archivo/video_archivo/file/imagen/banner deben
    apuntar a /api/media/ (gateway autenticado) y nunca a /media/ directo —
    si se filtrara /media/ sin autenticación, cualquiera con el link vería
    el archivo sin pasar por el JWT."""

    def test_imagen_archivo_de_bloque_usa_api_media(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin_a)
        imagen = SimpleUploadedFile('foto.png', _PNG_1X1, content_type='image/png')
        payload = {'tema': self.tema_a.id, 'tipo': self.tipo_texto.id, 'orden': 1, 'imagen_archivo': imagen}
        resp = self.client.post('/api/capacitacion/bloques/', payload, format='multipart')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(resp.data['imagen_archivo'].startswith('/api/media/'))

    def test_file_de_adjunto_usa_api_media(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin_a)
        bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_texto, orden=1)
        archivo = ContenidoBloqueArchivo.objects.create(
            bloque=bloque, orden=1, file=SimpleUploadedFile('doc.pdf', b'contenido'),
        )
        resp = self.client.get('/api/capacitacion/bloque-archivos/')
        self.assertEqual(resp.status_code, 200)
        encontrado = next(a for a in resp.data['results'] if a['id'] == archivo.id)
        self.assertTrue(encontrado['file'].startswith('/api/media/'))
