from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from capacitacion.models import ContenidoBloque, ContenidoBloqueArchivo
from .base import CapacitacionTestBase


class ContenidoBloqueArchivoTests(CapacitacionTestBase):
    """Reutiliza BaseFileEntity: mime_type/size/file_type se autodetectan al guardar."""

    def setUp(self):
        self.client = APIClient()
        self.bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_texto, orden=1)

    def test_subir_documento_autodetecta_metadata(self):
        archivo = SimpleUploadedFile('manual.pdf', b'%PDF-1.4 contenido falso', content_type='application/pdf')
        self.client.force_authenticate(self.admin_a)
        resp = self.client.post('/api/capacitacion/bloque-archivos/', {
            'bloque': self.bloque.id, 'orden': 1, 'file': archivo, 'description': 'Manual del colaborador',
        }, format='multipart')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['file_type'], 'document')
        self.assertEqual(resp.data['mime_type'], 'application/pdf')
        self.assertGreater(resp.data['size'], 0)

        archivo_db = ContenidoBloqueArchivo.objects.get(id=resp.data['id'])
        self.assertEqual(archivo_db.uploaded_by_id, self.admin_a.id)

    def test_colaborador_no_puede_subir_archivos(self):
        archivo = SimpleUploadedFile('x.pdf', b'contenido', content_type='application/pdf')
        self.client.force_authenticate(self.colaborador)
        resp = self.client.post('/api/capacitacion/bloque-archivos/', {
            'bloque': self.bloque.id, 'orden': 1, 'file': archivo,
        }, format='multipart')
        self.assertEqual(resp.status_code, 403)

    def test_borrar_archivo_cierra_el_hueco_de_orden(self):
        a1 = ContenidoBloqueArchivo.objects.create(
            bloque=self.bloque, orden=1, file=SimpleUploadedFile('a.pdf', b'x'),
        )
        a2 = ContenidoBloqueArchivo.objects.create(
            bloque=self.bloque, orden=2, file=SimpleUploadedFile('b.pdf', b'x'),
        )
        self.client.force_authenticate(self.admin_a)
        resp = self.client.delete(f'/api/capacitacion/bloque-archivos/{a1.id}/')
        self.assertEqual(resp.status_code, 204)
        a2.refresh_from_db()
        self.assertEqual(a2.orden, 1)
