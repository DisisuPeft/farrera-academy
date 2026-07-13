from rest_framework import serializers
from competencias.models import (
    Competencia, CompetenciaCurso, CompetenciaPuesto,
    RutaAprendizaje, RutaAprendizajeCurso, CompetenciaColaborador,
)


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


class RutaAprendizajeCursoSerializer(serializers.ModelSerializer):
    curso_titulo = serializers.CharField(source='curso.titulo', read_only=True)
    curso_duracion_horas = serializers.DecimalField(
        source='curso.duracion_horas', max_digits=6, decimal_places=2, read_only=True,
    )

    class Meta:
        model = RutaAprendizajeCurso
        fields = ('id', 'ruta', 'curso', 'curso_titulo', 'curso_duracion_horas', 'orden')


class RutaAprendizajeSerializer(serializers.ModelSerializer):
    competencia_nombre = serializers.CharField(source='competencia.nombre', read_only=True)
    nivel_objetivo_nombre = serializers.CharField(source='nivel_objetivo.nombre', read_only=True)
    nivel_objetivo_orden = serializers.IntegerField(source='nivel_objetivo.orden', read_only=True)
    cursos = RutaAprendizajeCursoSerializer(source='ruta_cursos', many=True, read_only=True)

    class Meta:
        model = RutaAprendizaje
        fields = (
            'id', 'nombre', 'descripcion',
            'competencia', 'competencia_nombre',
            'nivel_objetivo', 'nivel_objetivo_nombre', 'nivel_objetivo_orden',
            'cursos',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')


class CompetenciaColaboradorSerializer(serializers.ModelSerializer):
    competencia_nombre = serializers.CharField(source='competencia.nombre', read_only=True)
    competencia_codigo = serializers.CharField(source='competencia.codigo', read_only=True)
    nivel_nombre = serializers.CharField(source='nivel.nombre', read_only=True)
    nivel_orden = serializers.IntegerField(source='nivel.orden', read_only=True)
    origen_curso_titulo = serializers.CharField(
        source='origen.curso.titulo', read_only=True, default=None,
    )

    class Meta:
        model = CompetenciaColaborador
        fields = (
            'id', 'colaborador',
            'competencia', 'competencia_nombre', 'competencia_codigo',
            'nivel', 'nivel_nombre', 'nivel_orden',
            'origen', 'origen_curso_titulo',
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
