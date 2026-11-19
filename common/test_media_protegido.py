from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from capacitacion.tests.base import hacer_usuario
from sistema.models import Empresa, Dependencia


class MediaProtegidaTests(TestCase):
    """/api/media/<ruta> exige autenticación (header o cookie, igual que el
    resto de la API) y, si el usuario está autenticado, delega el archivo real
    a Nginx vía X-Accel-Redirect en vez de servirlo Django mismo — así Nginx
    puede mantener `location /media/ { internal; ... }` bloqueado al público
    y solo esta vista decide quién pasa."""

    def setUp(self):
        self.client = APIClient()
        empresa = Empresa.objects.create(razon_social='E', slug='e-media-test')
        dependencia = Dependencia.objects.create(nombre='D', empresa=empresa)
        self.user = hacer_usuario(dependencia)

    def test_sin_autenticar_devuelve_401(self):
        resp = self.client.get('/api/media/capacitacion/imagenes/bloques/algo.jpg')
        self.assertEqual(resp.status_code, 401)

    def test_autenticado_devuelve_x_accel_redirect_y_sin_cuerpo(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get('/api/media/capacitacion/imagenes/bloques/algo.jpg')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['X-Accel-Redirect'], '/media/capacitacion/imagenes/bloques/algo.jpg')
        self.assertEqual(resp.content, b'')

    def test_bloquea_path_traversal(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get('/api/media/../../../../etc/passwd')
        self.assertEqual(resp.status_code, 404)

    @override_settings(DEBUG=True)
    def test_en_debug_sirve_el_archivo_real_sin_nginx(self):
        ruta_relativa = 'capacitacion/imagenes/bloques/prueba-debug.txt'
        ruta_absoluta = settings.MEDIA_ROOT / ruta_relativa
        ruta_absoluta.parent.mkdir(parents=True, exist_ok=True)
        ruta_absoluta.write_text('contenido de prueba')
        self.addCleanup(ruta_absoluta.unlink)

        self.client.force_authenticate(self.user)
        resp = self.client.get(f'/api/media/{ruta_relativa}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b''.join(resp.streaming_content), b'contenido de prueba')
