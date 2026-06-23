from rest_framework import serializers
from catalogos.models import (
    Genero,
    EstadoPais,
    Localidad,
    CatalogStatus,
    TipoBloqueContenido,
    TipeTema,
    TipoEvaluacion,
    NivelCompetencia,
)


class GeneroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genero
        fields = ('id', 'nombre', 'status')


class EstadoPaisSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoPais
        fields = ('id', 'name', 'status')


class LocalidadSerializer(serializers.ModelSerializer):
    estado_nombre = serializers.CharField(source='country.name', read_only=True)

    class Meta:
        model = Localidad
        fields = ('id', 'country', 'estado_nombre', 'name', 'clave', 'status')


class _BaseCatalogoSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('id', 'nombre', 'codigo', 'icono', 'color', 'orden', 'activo', 'creado_at', 'actualizado_at')
        read_only_fields = ('creado_at', 'actualizado_at')


class CatalogStatusSerializer(_BaseCatalogoSerializer):
    class Meta(_BaseCatalogoSerializer.Meta):
        model = CatalogStatus


class TipoBloqueContenidoSerializer(_BaseCatalogoSerializer):
    class Meta(_BaseCatalogoSerializer.Meta):
        model = TipoBloqueContenido


class TipeTemaSerializer(_BaseCatalogoSerializer):
    class Meta(_BaseCatalogoSerializer.Meta):
        model = TipeTema


class TipoEvaluacionSerializer(_BaseCatalogoSerializer):
    class Meta(_BaseCatalogoSerializer.Meta):
        model = TipoEvaluacion


class NivelCompetenciaSerializer(_BaseCatalogoSerializer):
    class Meta(_BaseCatalogoSerializer.Meta):
        model = NivelCompetencia
