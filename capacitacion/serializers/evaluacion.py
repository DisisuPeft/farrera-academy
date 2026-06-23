from rest_framework import serializers
from capacitacion.models import Evaluacion, Pregunta, OpcionPregunta


class EvaluacionSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)

    class Meta:
        model = Evaluacion
        fields = (
            'id', 'titulo', 'tipo', 'tipo_nombre', 'puntaje_minimo',
            'curso', 'modulo',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')


class PreguntaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pregunta
        fields = (
            'id', 'evaluacion', 'texto', 'orden',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')


class OpcionPreguntaSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionPregunta
        fields = (
            'id', 'pregunta', 'texto', 'orden', 'es_correcta',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')
