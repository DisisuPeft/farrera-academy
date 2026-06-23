from rest_framework import serializers
from capacitacion.models import Inscripcion, ProgresoTema, ResultadoEvaluacion


class InscripcionSerializer(serializers.ModelSerializer):
    curso_titulo = serializers.CharField(source='curso.titulo', read_only=True)
    colaborador_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        fields = (
            'id', 'colaborador', 'colaborador_nombre',
            'curso', 'curso_titulo',
            'inscrito_at', 'completado_at',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('inscrito_at', 'creado_at', 'actualizado_at')

    def get_colaborador_nombre(self, obj):
        return obj.colaborador.get_full_name() or obj.colaborador.username


class ProgresoTemaSerializer(serializers.ModelSerializer):
    tema_titulo = serializers.CharField(source='tema.titulo', read_only=True)
    colaborador_nombre = serializers.SerializerMethodField()

    class Meta:
        model = ProgresoTema
        fields = (
            'id', 'colaborador', 'colaborador_nombre',
            'tema', 'tema_titulo',
            'completado_at',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('completado_at', 'creado_at', 'actualizado_at')

    def get_colaborador_nombre(self, obj):
        return obj.colaborador.get_full_name() or obj.colaborador.username


class ResultadoEvaluacionSerializer(serializers.ModelSerializer):
    evaluacion_titulo = serializers.CharField(source='evaluacion.titulo', read_only=True)
    colaborador_nombre = serializers.SerializerMethodField()
    puntaje = serializers.SerializerMethodField()

    class Meta:
        model = ResultadoEvaluacion
        fields = (
            'id', 'colaborador', 'colaborador_nombre',
            'evaluacion', 'evaluacion_titulo',
            'correctas', 'total', 'puntaje',
            'presentado_at',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('presentado_at', 'creado_at', 'actualizado_at')

    def get_colaborador_nombre(self, obj):
        return obj.colaborador.get_full_name() or obj.colaborador.username

    def get_puntaje(self, obj):
        if not obj.total:
            return 0
        return round((obj.correctas / obj.total) * 100, 2)
