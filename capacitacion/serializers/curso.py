from rest_framework import serializers
from capacitacion.models import (
    Curso, Modulo, Tema,
    ContenidoBloque, ContenidoBloqueItem, ContenidoBloqueArchivo, ContenidoBloqueOpcion,
)
from common.serializers import ArchivoProtegidoField, ImagenProtegidaField


class CursoSerializer(serializers.ModelSerializer):
    status_nombre = serializers.CharField(source='status.nombre', read_only=True)
    imagen = ImagenProtegidaField(required=False, allow_null=True)
    banner = ImagenProtegidaField(required=False, allow_null=True)

    class Meta:
        model = Curso
        fields = (
            'id', 'titulo', 'descripcion', 'duracion_horas',
            'imagen', 'banner', 'status', 'status_nombre',
            'empresa', 'creado_por',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_por', 'creado_at', 'actualizado_at')


class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = (
            'id', 'curso', 'titulo', 'descripcion', 'orden',
            'horas_teoricas', 'horas_practicas', 'tiene_evaluacion',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')


class TemaSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)

    class Meta:
        model = Tema
        fields = (
            'id', 'modulo', 'titulo', 'duracion_estimada',
            'tipo', 'tipo_nombre', 'orden',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')


class ContenidoBloqueItemSerializer(serializers.ModelSerializer):
    imagen_archivo = ImagenProtegidaField(required=False, allow_null=True)

    class Meta:
        model = ContenidoBloqueItem
        fields = (
            'id', 'bloque', 'orden', 'titulo', 'texto',
            'imagen_url', 'imagen_archivo', 'items',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('activo', 'creado_at', 'actualizado_at')


class ContenidoBloqueArchivoSerializer(serializers.ModelSerializer):
    file = ArchivoProtegidoField()

    class Meta:
        model = ContenidoBloqueArchivo
        # Nota: ContenidoBloqueArchivo hereda de BaseFileEntity -> Base (created_at/status),
        # NO de BaseModel (creado_at/activo) como el resto de capacitacion.models.
        fields = (
            'id', 'bloque', 'orden', 'file', 'original_name', 'mime_type',
            'size', 'size_formatted', 'file_type', 'description', 'checksum',
            'status', 'created_at',
        )
        read_only_fields = (
            'original_name', 'mime_type', 'size', 'size_formatted',
            'file_type', 'checksum', 'created_at',
        )


class ContenidoBloqueOpcionSerializer(serializers.ModelSerializer):
    """Autoría de opciones para bloques 'opcion-multiple'/'verdadero-falso'.
    Incluye `es_correcta` — SOLO para el admin, nunca para el colaborador
    (ver ContenidoBloqueOpcionColaboradorSerializer en serializers/colaborador.py)."""

    class Meta:
        model = ContenidoBloqueOpcion
        fields = (
            'id', 'bloque', 'orden', 'texto', 'es_correcta',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('activo', 'creado_at', 'actualizado_at')


class ContenidoBloqueSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)
    tipo_codigo = serializers.CharField(source='tipo.codigo', read_only=True)
    bloque_items = ContenidoBloqueItemSerializer(many=True, read_only=True)
    archivos = ContenidoBloqueArchivoSerializer(many=True, read_only=True)
    opciones = ContenidoBloqueOpcionSerializer(many=True, read_only=True)
    video_archivo = ArchivoProtegidoField(required=False, allow_null=True)
    imagen_archivo = ImagenProtegidaField(required=False, allow_null=True)

    class Meta:
        model = ContenidoBloque
        fields = (
            'id', 'tema', 'tipo', 'tipo_nombre', 'tipo_codigo', 'orden',
            'texto', 'variante', 'items', 'filas',
            'video_url', 'video_archivo', 'imagen_url', 'imagen_archivo', 'embed_url',
            'bloque_items', 'archivos', 'opciones',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('activo', 'creado_at', 'actualizado_at')
