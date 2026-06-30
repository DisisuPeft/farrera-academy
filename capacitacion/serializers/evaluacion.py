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

    def validate(self, attrs):
        curso = attrs.get('curso', getattr(self.instance, 'curso', None))
        modulo = attrs.get('modulo', getattr(self.instance, 'modulo', None))
        if curso and modulo:
            raise serializers.ValidationError(
                'Una evaluación no puede pertenecer a un curso y a un módulo al mismo tiempo.'
            )
        if not curso and not modulo:
            raise serializers.ValidationError(
                'Una evaluación debe pertenecer a un curso o a un módulo.'
            )
        return attrs


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
