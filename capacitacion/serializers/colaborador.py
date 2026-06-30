from rest_framework import serializers
from capacitacion.models import (
    Inscripcion, ProgresoTema, ResultadoEvaluacion,
    Curso, Modulo, Tema, ContenidoBloque,
    Evaluacion, Pregunta, OpcionPregunta,
)
from competencias.models import CompetenciaCurso


class MiInscripcionSerializer(serializers.ModelSerializer):
    curso_titulo = serializers.CharField(source='curso.titulo', read_only=True)

    class Meta:
        model = Inscripcion
        fields = ('id', 'curso', 'curso_titulo', 'inscrito_at', 'completado_at', 'activo')
        read_only_fields = ('inscrito_at', 'activo')


class MiProgresoTemaSerializer(serializers.ModelSerializer):
    tema_titulo = serializers.CharField(source='tema.titulo', read_only=True)

    class Meta:
        model = ProgresoTema
        fields = ('id', 'tema', 'tema_titulo', 'completado_at', 'activo')
        read_only_fields = ('completado_at', 'activo')


class _RespuestaInputSerializer(serializers.Serializer):
    pregunta = serializers.PrimaryKeyRelatedField(queryset=Pregunta.objects.all())
    opcion = serializers.PrimaryKeyRelatedField(queryset=OpcionPregunta.objects.all())


class MiResultadoEvaluacionSerializer(serializers.ModelSerializer):
    evaluacion_titulo = serializers.CharField(source='evaluacion.titulo', read_only=True)
    puntaje = serializers.SerializerMethodField()
    respuestas = _RespuestaInputSerializer(many=True, write_only=True)

    class Meta:
        model = ResultadoEvaluacion
        fields = (
            'id', 'evaluacion', 'evaluacion_titulo',
            'correctas', 'total', 'puntaje',
            'presentado_at', 'activo',
            'respuestas',
        )
        read_only_fields = ('correctas', 'total', 'presentado_at', 'activo')

    def get_puntaje(self, obj):
        if not obj.total:
            return 0
        return round((obj.correctas / obj.total) * 100, 2)

    def validate(self, data):
        evaluacion = data['evaluacion']
        respuestas = data.get('respuestas', [])

        preguntas_evaluacion = set(evaluacion.preguntas.values_list('id', flat=True))
        preguntas_respondidas = {r['pregunta'].id for r in respuestas}

        if preguntas_respondidas != preguntas_evaluacion:
            raise serializers.ValidationError(
                {'respuestas': 'Debes responder todas las preguntas de la evaluación.'}
            )

        for r in respuestas:
            if r['opcion'].pregunta_id != r['pregunta'].id:
                raise serializers.ValidationError(
                    {'respuestas': f"La opción {r['opcion'].id} no pertenece a la pregunta {r['pregunta'].id}."}
                )

        return data

    def create(self, validated_data):
        respuestas = validated_data.pop('respuestas')
        evaluacion = validated_data['evaluacion']

        total = evaluacion.preguntas.count()
        correctas = sum(1 for r in respuestas if r['opcion'].es_correcta)

        return ResultadoEvaluacion.objects.create(
            **validated_data,
            correctas=correctas,
            total=total,
        )


# ---------------------------------------------------------------------------
# Serializers de lectura (contenido del curso para colaboradores)
# ---------------------------------------------------------------------------

class _CompetenciaCursoResumenSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='competencia.nombre', read_only=True)
    codigo = serializers.CharField(source='competencia.codigo', read_only=True)
    icono = serializers.CharField(source='competencia.icono', read_only=True)
    color = serializers.CharField(source='competencia.color', read_only=True)
    nivel = serializers.CharField(source='nivel.nombre', read_only=True)

    class Meta:
        model = CompetenciaCurso
        fields = ('nombre', 'codigo', 'icono', 'color', 'nivel')


class CursoColaboradorSerializer(serializers.ModelSerializer):
    status_nombre = serializers.CharField(source='status.nombre', read_only=True)
    competencias = _CompetenciaCursoResumenSerializer(
        source='competencia_cursos', many=True, read_only=True,
    )
    inscrito = serializers.SerializerMethodField()
    progreso = serializers.SerializerMethodField()

    class Meta:
        model = Curso
        fields = (
            'id', 'titulo', 'descripcion', 'duracion_horas',
            'imagen', 'banner', 'status_nombre',
            'competencias', 'inscrito', 'progreso',
        )

    def get_inscrito(self, obj):
        user = self.context['request'].user
        return obj.inscripciones.filter(colaborador=user, activo=True).exists()

    def get_progreso(self, obj):
        user = self.context['request'].user

        temas_total = Tema.objects.filter(modulo__curso=obj, activo=True).count()
        temas_completados = ProgresoTema.objects.filter(colaborador=user, tema__modulo__curso=obj).count()

        modulos_con_eval = Modulo.objects.filter(curso=obj, tiene_evaluacion=True, activo=True).count()
        evals_modulo_hechas = (
            ResultadoEvaluacion.objects
            .filter(colaborador=user, evaluacion__modulo__curso=obj, evaluacion__modulo__isnull=False)
            .values('evaluacion__modulo')
            .distinct()
            .count()
        )

        tiene_eval_final = Evaluacion.objects.filter(curso=obj, modulo__isnull=True, activo=True).exists()
        eval_final_hecha = (
            ResultadoEvaluacion.objects.filter(
                colaborador=user, evaluacion__curso=obj, evaluacion__modulo__isnull=True,
            ).exists()
            if tiene_eval_final else False
        )

        total = temas_total + modulos_con_eval + (1 if tiene_eval_final else 0)
        completados = temas_completados + evals_modulo_hechas + (1 if eval_final_hecha else 0)
        porcentaje = round((completados / total) * 100) if total else 0
        return {'completados': completados, 'total': total, 'porcentaje': porcentaje}


class ModuloColaboradorSerializer(serializers.ModelSerializer):
    progreso = serializers.SerializerMethodField()

    class Meta:
        model = Modulo
        fields = ('id', 'curso', 'titulo', 'descripcion', 'orden', 'horas_teoricas', 'horas_practicas', 'tiene_evaluacion', 'progreso')

    def get_progreso(self, obj):
        user = self.context['request'].user

        temas_total = Tema.objects.filter(modulo=obj, activo=True).count()
        temas_completados = ProgresoTema.objects.filter(colaborador=user, tema__modulo=obj).count()

        if obj.tiene_evaluacion:
            total = temas_total + 1
            eval_hecha = ResultadoEvaluacion.objects.filter(
                colaborador=user, evaluacion__modulo=obj,
            ).exists()
            completados = temas_completados + (1 if eval_hecha else 0)
        else:
            total = temas_total
            completados = temas_completados

        porcentaje = round((completados / total) * 100) if total else 0
        return {'completados': completados, 'total': total, 'porcentaje': porcentaje}


class TemaColaboradorSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)

    class Meta:
        model = Tema
        fields = ('id', 'modulo', 'titulo', 'duracion_estimada', 'tipo_nombre', 'orden')


class ContenidoBloqueColaboradorSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)

    class Meta:
        model = ContenidoBloque
        fields = ('id', 'tema', 'tipo_nombre', 'orden', 'texto', 'variante', 'items', 'filas', 'video_url', 'video_archivo')


class OpcionColaboradorSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionPregunta
        fields = ('id', 'texto', 'orden')  # sin es_correcta


class PreguntaColaboradorSerializer(serializers.ModelSerializer):
    opciones = OpcionColaboradorSerializer(many=True, read_only=True)

    class Meta:
        model = Pregunta
        fields = ('id', 'evaluacion', 'texto', 'orden', 'opciones')


class EvaluacionColaboradorSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)

    class Meta:
        model = Evaluacion
        fields = ('id', 'titulo', 'tipo_nombre', 'puntaje_minimo', 'curso', 'modulo')
