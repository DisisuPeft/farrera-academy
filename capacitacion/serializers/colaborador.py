from rest_framework import serializers
from capacitacion.models import (
    Inscripcion, ProgresoTema, ResultadoEvaluacion,
    Curso, Modulo, Tema, ContenidoBloque, ContenidoBloqueItem, ContenidoBloqueArchivo,
    ContenidoBloqueOpcion, ContenidoBloqueRespuesta,
    Evaluacion, Pregunta, OpcionPregunta,
)
from competencias.models import CompetenciaCurso


def _hay_intento_aprobado(resultados):
    """Un intento cuenta como 'completado' en el progreso visual solo si
    alcanzó evaluacion.puntaje_minimo — no por el mero hecho de existir.
    Debe coincidir con el criterio real de acreditación en
    FinalizacionService._criterio_cumplido, o la barra de progreso del
    colaborador mentiría sobre lo que falta para acreditarse."""
    return any(
        r.total > 0 and (r.correctas / r.total) * 100 >= r.evaluacion.puntaje_minimo
        for r in resultados
    )


class MiInscripcionSerializer(serializers.ModelSerializer):
    curso_titulo = serializers.CharField(source='curso.titulo', read_only=True)

    class Meta:
        model = Inscripcion
        fields = ('id', 'curso', 'curso_titulo', 'inscrito_at', 'completado_at', 'activo')
        read_only_fields = ('curso', 'inscrito_at', 'completado_at', 'activo')


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
        ids_preguntas_respondidas = [r['pregunta'].id for r in respuestas]

        if len(ids_preguntas_respondidas) != len(set(ids_preguntas_respondidas)):
            raise serializers.ValidationError(
                {'respuestas': 'No puedes responder la misma pregunta más de una vez.'}
            )

        if set(ids_preguntas_respondidas) != preguntas_evaluacion:
            raise serializers.ValidationError(
                {'respuestas': 'Debes responder todas las preguntas de la evaluación.'}
            )

        for r in respuestas:
            if r['opcion'].pregunta_id != r['pregunta'].id:
                raise serializers.ValidationError(
                    {'respuestas': f"La opción {r['opcion'].id} no pertenece a la pregunta {r['pregunta'].id}."}
                )

        return data


class MiRespuestaBloqueSerializer(serializers.ModelSerializer):
    """
    Intento de un colaborador sobre un bloque evaluativo embebido
    ('opcion-multiple'/'verdadero-falso'). Igual que MiResultadoEvaluacionSerializer:
    el cliente solo manda qué opción eligió, `es_correcta` se calcula en el
    servidor y nunca se recibe del cliente.
    """
    bloque_texto = serializers.CharField(source='bloque.texto', read_only=True)

    class Meta:
        model = ContenidoBloqueRespuesta
        fields = (
            'id', 'bloque', 'bloque_texto', 'opcion_seleccionada',
            'es_correcta', 'respondido_at', 'activo',
        )
        read_only_fields = ('es_correcta', 'respondido_at', 'activo')

    def validate(self, data):
        bloque = data['bloque']
        opcion = data['opcion_seleccionada']
        if opcion.bloque_id != bloque.id:
            raise serializers.ValidationError(
                {'opcion_seleccionada': 'Esa opción no pertenece al bloque indicado.'}
            )
        return data

    def create(self, validated_data):
        opcion = validated_data['opcion_seleccionada']
        return ContenidoBloqueRespuesta.objects.create(
            **validated_data,
            es_correcta=opcion.es_correcta,
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


def _inscripcion_reciente(user, curso):
    """La inscripción más reciente del colaborador a ese curso, o None si no
    tiene ninguna. `inscrito`/`progreso` se calculan sobre esta — nunca
    sobre la unión de todas las inscripciones al mismo curso (spec
    Acceptance, horneado tras `analyze`)."""
    return Inscripcion.objects.filter(colaborador=user, curso=curso).order_by('-inscrito_at', '-pk').first()


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
        inscripcion = _inscripcion_reciente(user, obj)
        return inscripcion is not None and inscripcion.activo

    def get_progreso(self, obj):
        user = self.context['request'].user
        inscripcion = _inscripcion_reciente(user, obj)

        temas_total = Tema.objects.filter(modulo__curso=obj, activo=True).count()
        modulos_con_eval = Modulo.objects.filter(curso=obj, tiene_evaluacion=True, activo=True).count()
        tiene_eval_final = Evaluacion.objects.filter(curso=obj, modulo__isnull=True, activo=True).exists()
        total = temas_total + modulos_con_eval + (1 if tiene_eval_final else 0)

        if inscripcion is None:
            return {'completados': 0, 'total': total, 'porcentaje': 0}

        temas_completados = ProgresoTema.objects.filter(inscripcion=inscripcion, tema__modulo__curso=obj).count()

        resultados_modulo = (
            ResultadoEvaluacion.objects
            .filter(inscripcion=inscripcion, evaluacion__modulo__curso=obj, evaluacion__modulo__isnull=False)
            .select_related('evaluacion')
        )
        modulos_aprobados = {
            r.evaluacion.modulo_id for r in resultados_modulo
            if r.total > 0 and (r.correctas / r.total) * 100 >= r.evaluacion.puntaje_minimo
        }
        evals_modulo_hechas = len(modulos_aprobados)

        eval_final_hecha = (
            _hay_intento_aprobado(
                ResultadoEvaluacion.objects.filter(
                    inscripcion=inscripcion, evaluacion__curso=obj, evaluacion__modulo__isnull=True,
                ).select_related('evaluacion')
            )
            if tiene_eval_final else False
        )

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
        inscripcion = _inscripcion_reciente(user, obj.curso)

        temas_total = Tema.objects.filter(modulo=obj, activo=True).count()
        total = temas_total + 1 if obj.tiene_evaluacion else temas_total

        if inscripcion is None:
            return {'completados': 0, 'total': total, 'porcentaje': 0}

        temas_completados = ProgresoTema.objects.filter(inscripcion=inscripcion, tema__modulo=obj).count()

        if obj.tiene_evaluacion:
            eval_aprobada = _hay_intento_aprobado(
                ResultadoEvaluacion.objects.filter(
                    inscripcion=inscripcion, evaluacion__modulo=obj,
                ).select_related('evaluacion')
            )
            completados = temas_completados + (1 if eval_aprobada else 0)
        else:
            completados = temas_completados

        porcentaje = round((completados / total) * 100) if total else 0
        return {'completados': completados, 'total': total, 'porcentaje': porcentaje}


class TemaColaboradorSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)

    class Meta:
        model = Tema
        fields = ('id', 'modulo', 'titulo', 'duracion_estimada', 'tipo_nombre', 'orden')


class ContenidoBloqueItemColaboradorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContenidoBloqueItem
        fields = ('id', 'orden', 'titulo', 'texto', 'imagen_url', 'imagen_archivo', 'items')


class ContenidoBloqueArchivoColaboradorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContenidoBloqueArchivo
        fields = ('id', 'orden', 'file', 'original_name', 'mime_type', 'size_formatted', 'file_type', 'description')


class ContenidoBloqueOpcionColaboradorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContenidoBloqueOpcion
        fields = ('id', 'orden', 'texto')  # sin es_correcta


class ContenidoBloqueColaboradorSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)
    tipo_codigo = serializers.CharField(source='tipo.codigo', read_only=True)
    video_stream_url = serializers.SerializerMethodField()
    bloque_items = ContenidoBloqueItemColaboradorSerializer(many=True, read_only=True)
    archivos = ContenidoBloqueArchivoColaboradorSerializer(many=True, read_only=True)
    opciones = ContenidoBloqueOpcionColaboradorSerializer(many=True, read_only=True)

    class Meta:
        model = ContenidoBloque
        fields = (
            'id', 'tema', 'tipo_nombre', 'tipo_codigo', 'orden', 'texto', 'variante',
            'items', 'filas', 'video_url', 'video_stream_url',
            'imagen_url', 'imagen_archivo', 'embed_url', 'bloque_items', 'archivos', 'opciones',
        )

    def get_video_stream_url(self, obj):
        if not obj.video_archivo:
            return None
        request = self.context.get('request')
        if request is None:
            return None
        return request.build_absolute_uri(f'/api/capacitacion/stream/{obj.pk}/')


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
        fields = ('id', 'titulo', 'tipo_nombre', 'puntaje_minimo', 'intentos_maximos', 'curso', 'modulo')
