from rest_framework import serializers
from capacitacion.models import Curso, Modulo, Tema, ContenidoBloque


class CursoSerializer(serializers.ModelSerializer):
    status_nombre = serializers.CharField(source='status.nombre', read_only=True)

    class Meta:
        model = Curso
        fields = (
            'id', 'titulo', 'descripcion', 'duracion_horas',
            'imagen', 'banner', 'status', 'status_nombre',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')


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


class ContenidoBloqueSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)

    class Meta:
        model = ContenidoBloque
        fields = (
            'id', 'tema', 'tipo', 'tipo_nombre', 'orden',
            'texto', 'variante', 'items', 'filas', 'video_url', 'video_archivo',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')
