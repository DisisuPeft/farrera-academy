from rest_framework import serializers
from competencias.models import Competencia, CompetenciaCurso, CompetenciaPuesto


class CompetenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competencia
        fields = (
            'id', 'nombre', 'codigo', 'descripcion',
            'icono', 'color', 'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')


class CompetenciaCursoSerializer(serializers.ModelSerializer):
    competencia_nombre = serializers.CharField(source='competencia.nombre', read_only=True)
    curso_titulo = serializers.CharField(source='curso.titulo', read_only=True)
    nivel_nombre = serializers.CharField(source='nivel.nombre', read_only=True)

    class Meta:
        model = CompetenciaCurso
        fields = (
            'id', 'competencia', 'competencia_nombre',
            'curso', 'curso_titulo',
            'nivel', 'nivel_nombre',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')


class CompetenciaPuestoSerializer(serializers.ModelSerializer):
    competencia_nombre = serializers.CharField(source='competencia.nombre', read_only=True)
    puesto_nombre = serializers.CharField(source='puesto.nombre', read_only=True)
    nivel_nombre = serializers.CharField(source='nivel.nombre', read_only=True)

    class Meta:
        model = CompetenciaPuesto
        fields = (
            'id', 'competencia', 'competencia_nombre',
            'puesto', 'puesto_nombre',
            'nivel', 'nivel_nombre',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')
