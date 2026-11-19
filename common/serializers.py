from rest_framework import serializers


class _MediaProtegidaMixin:
    """Mismo archivo subido, pero expone su URL bajo /api/media/<ruta> (la
    vista MediaProtegidaView) en vez de la /media/<ruta> directa de Django —
    así Nginx puede mantener `location /media/ { internal; }` y solo un
    usuario autenticado llega al archivo real."""

    def to_representation(self, value):
        if not value:
            return None
        return f'/api/media/{value.name}'


class ImagenProtegidaField(_MediaProtegidaMixin, serializers.ImageField):
    pass


class ArchivoProtegidoField(_MediaProtegidaMixin, serializers.FileField):
    pass
