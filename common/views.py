import mimetypes
import posixpath

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from user.authenticate import CustomJWTAuthentication


class MediaProtegidaView(APIView):
    """
    Gateway de autenticación para /media/: Nginx mantiene
    `location /media/ { internal; ... }` (nadie entra directo), y esta vista
    es el único camino público — exige el mismo JWT (header o cookie) que el
    resto de la API y, si es válido, delega el archivo real a Nginx vía
    X-Accel-Redirect en vez de leerlo/transmitirlo Django mismo. Mismo patrón
    que VideoStreamView (capacitacion/views.py) para el streaming de video,
    pero genérico para cualquier archivo bajo MEDIA_ROOT (imágenes, adjuntos).
    En DEBUG (local, sin Nginx delante) sirve el archivo directo.
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, ruta):
        ruta_normalizada = posixpath.normpath('/' + ruta).lstrip('/')
        if ruta_normalizada != ruta.lstrip('/') or ruta_normalizada.startswith('..'):
            raise Http404

        if settings.DEBUG:
            ruta_absoluta = settings.MEDIA_ROOT / ruta_normalizada
            if not ruta_absoluta.is_file():
                raise Http404
            content_type, _ = mimetypes.guess_type(str(ruta_absoluta))
            return FileResponse(ruta_absoluta.open('rb'), content_type=content_type)

        response = HttpResponse()
        response['Content-Type'] = ''
        response['X-Accel-Redirect'] = f'{settings.MEDIA_URL}{ruta_normalizada}'
        return response
