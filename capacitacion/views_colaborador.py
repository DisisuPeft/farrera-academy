from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from user.authenticate import CustomJWTAuthentication

from capacitacion.models import (
    Inscripcion, Periodo, ProgresoTema, ResultadoEvaluacion,
    Curso, Modulo, Tema, ContenidoBloque, ContenidoBloqueRespuesta,
    Evaluacion, Pregunta,
)
from capacitacion.serializers import (
    MiInscripcionSerializer,
    MiProgresoTemaSerializer,
    MiResultadoEvaluacionSerializer,
    CursoColaboradorSerializer,
    ModuloColaboradorSerializer,
    TemaColaboradorSerializer,
    ContenidoBloqueColaboradorSerializer,
    MiRespuestaBloqueSerializer,
    EvaluacionColaboradorSerializer,
    PreguntaColaboradorSerializer,
)
from capacitacion.services.evidencia_service import (
    ContenidoAjeno, EvidenciaService, InscripcionNoEncontrada, IntentosAgotados,
)
from capacitacion.services.inscripcion_service import InscripcionDuplicada, InscripcionService, PeriodoNoAbierto


class _BaseColaboradorViewSet(ModelViewSet):
    """ViewSet base para colaboradores: solo ven y operan sus propios registros."""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    # No permite DELETE en ningún endpoint de colaborador
    http_method_names = ['get', 'post', 'patch', 'head', 'options']


class MisInscripcionesViewSet(_BaseColaboradorViewSet):
    """
    GET  /mis-inscripciones/          → cursos en los que está inscrito
    POST /mis-inscripciones/          → auto-inscribirse a un curso { "curso": <id> }

    `completado_at` es de solo lectura: la finalización la decide
    `FinalizacionService`, nunca el colaborador directamente (AC10).
    """
    serializer_class = MiInscripcionSerializer

    def get_queryset(self):
        return (
            Inscripcion.objects
            .select_related('curso')
            .filter(colaborador=self.request.user)
        )

    def create(self, request, *args, **kwargs):
        curso_id = request.data.get('curso')
        periodo = (
            Periodo.objects
            .filter(curso_id=curso_id, estado=Periodo.Estado.ABIERTO)
            .order_by('-fecha_inicio')
            .first()
        )
        if periodo is None:
            return Response(
                {'detail': 'No hay un periodo abierto para este curso.'}, status=status.HTTP_400_BAD_REQUEST,
            )

        resultado = InscripcionService.crear(colaborador=request.user, periodo=periodo)
        if isinstance(resultado, PeriodoNoAbierto):
            return Response(
                {'detail': 'El periodo ya no está abierto.'}, status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(resultado, InscripcionDuplicada):
            return Response(
                {'detail': 'Ya estás inscrito en este periodo.'}, status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(resultado)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MisProgresosViewSet(_BaseColaboradorViewSet):
    """
    GET  /mis-progresos/      → temas completados
    POST /mis-progresos/      → marcar tema como completado { "tema": <id> }
    """
    serializer_class = MiProgresoTemaSerializer
    http_method_names = ['get', 'post', 'head', 'options']  # sin PATCH

    def get_queryset(self):
        return (
            ProgresoTema.objects
            .select_related('tema')
            .filter(inscripcion__colaborador=self.request.user)
        )

    def create(self, request, *args, **kwargs):
        tema_id = request.data.get('tema')
        tema = Tema.objects.filter(pk=tema_id).first()
        if tema is None:
            return Response({'tema': ['Tema inválido.']}, status=status.HTTP_400_BAD_REQUEST)

        resultado = EvidenciaService.registrar_progreso(colaborador=request.user, tema=tema)
        if isinstance(resultado, InscripcionNoEncontrada):
            return Response(
                {'detail': 'No tienes una inscripción activa para el curso de este tema.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(resultado, ContenidoAjeno):
            return Response(
                {'detail': 'Ese tema no pertenece al curso de tu inscripción activa.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(resultado)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MisResultadosViewSet(_BaseColaboradorViewSet):
    """
    GET  /mis-resultados/     → resultados de evaluaciones
    POST /mis-resultados/     → enviar resultado { "evaluacion": <id>, "correctas": N, "total": N }
    """
    serializer_class = MiResultadoEvaluacionSerializer
    http_method_names = ['get', 'post', 'head', 'options']  # sin PATCH

    def get_queryset(self):
        return (
            ResultadoEvaluacion.objects
            .select_related('evaluacion')
            .filter(inscripcion__colaborador=self.request.user)
        )

    def create(self, request, *args, **kwargs):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        respuestas = input_serializer.validated_data['respuestas']
        evaluacion = input_serializer.validated_data['evaluacion']
        total = evaluacion.preguntas.count()
        correctas = sum(1 for r in respuestas if r['opcion'].es_correcta)

        resultado = EvidenciaService.registrar_resultado_evaluacion(
            colaborador=request.user, evaluacion=evaluacion, correctas=correctas, total=total,
        )
        if isinstance(resultado, InscripcionNoEncontrada):
            return Response(
                {'detail': 'No tienes una inscripción activa para el curso de esta evaluación.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(resultado, ContenidoAjeno):
            return Response(
                {'detail': 'Esa evaluación no pertenece al curso de tu inscripción activa.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(resultado, IntentosAgotados):
            return Response(
                {'detail': 'Ya agotaste los intentos permitidos para esta evaluación.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_serializer = self.get_serializer(resultado)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class MisRespuestasBloqueViewSet(_BaseColaboradorViewSet):
    """
    GET  /mis-respuestas-bloque/      → mis intentos sobre bloques evaluativos embebidos
    POST /mis-respuestas-bloque/      → responder { "bloque": <id>, "opcion_seleccionada": <id> }
    (bloques tipo 'opcion-multiple'/'verdadero-falso', distinto del sistema formal de Evaluacion)
    """
    serializer_class = MiRespuestaBloqueSerializer
    http_method_names = ['get', 'post', 'head', 'options']  # sin PATCH: cada envío es un intento nuevo

    def get_queryset(self):
        return (
            ContenidoBloqueRespuesta.objects
            .select_related('bloque', 'opcion_seleccionada')
            .filter(inscripcion__colaborador=self.request.user)
        )

    def create(self, request, *args, **kwargs):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        bloque = input_serializer.validated_data['bloque']
        opcion = input_serializer.validated_data['opcion_seleccionada']

        resultado = EvidenciaService.registrar_respuesta_bloque(
            colaborador=request.user, bloque=bloque, opcion=opcion,
        )
        if isinstance(resultado, InscripcionNoEncontrada):
            return Response(
                {'detail': 'No tienes una inscripción activa para el curso de este bloque.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(resultado, ContenidoAjeno):
            return Response(
                {'opcion_seleccionada': 'Esa opción no pertenece al bloque indicado, o el bloque no pertenece '
                 'al curso de tu inscripción activa.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_serializer = self.get_serializer(resultado)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Lectura de contenido del curso (solo GET)
# ---------------------------------------------------------------------------

class _BaseReadOnlyViewSet(ReadOnlyModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]


def _base_cursos_qs():
    return (
        Curso.objects
        .select_related('status')
        .prefetch_related('competencia_cursos__competencia', 'competencia_cursos__nivel', 'inscripciones')
        .filter(activo=True)
    )


class CursoColaboradorViewSet(_BaseReadOnlyViewSet):
    """GET /cursos/ y /cursos/{id}/ — catálogo completo de cursos activos."""
    serializer_class = CursoColaboradorSerializer

    def get_queryset(self):
        return _base_cursos_qs()


class MisCursosViewSet(_BaseReadOnlyViewSet):
    """GET /mis-cursos/ — cursos que corresponden a las competencias del puesto del colaborador."""
    serializer_class = CursoColaboradorSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.puesto_id:
            return Curso.objects.none()
        return (
            _base_cursos_qs()
            .filter(competencia_cursos__competencia__competencia_puestos__puesto=user.puesto)
            .distinct()
        )


class ModuloColaboradorViewSet(_BaseReadOnlyViewSet):
    """GET /modulos/?curso={id} — módulos de un curso."""
    serializer_class = ModuloColaboradorSerializer

    def get_queryset(self):
        qs = Modulo.objects.filter(activo=True)
        curso = self.request.query_params.get('curso')
        if curso:
            qs = qs.filter(curso_id=curso)
        return qs


class TemaColaboradorViewSet(_BaseReadOnlyViewSet):
    """GET /temas/?modulo={id} — temas de un módulo."""
    serializer_class = TemaColaboradorSerializer

    def get_queryset(self):
        qs = Tema.objects.select_related('tipo').filter(activo=True)
        modulo = self.request.query_params.get('modulo')
        if modulo:
            qs = qs.filter(modulo_id=modulo)
        return qs


class ContenidoBloqueColaboradorViewSet(_BaseReadOnlyViewSet):
    """GET /bloques/?tema={id} — bloques de contenido de un tema."""
    serializer_class = ContenidoBloqueColaboradorSerializer

    def get_queryset(self):
        qs = (
            ContenidoBloque.objects
            .select_related('tipo')
            .prefetch_related('bloque_items', 'archivos', 'opciones')
            .filter(activo=True)
        )
        tema = self.request.query_params.get('tema')
        if tema:
            qs = qs.filter(tema_id=tema)
        return qs


class EvaluacionColaboradorViewSet(_BaseReadOnlyViewSet):
    """GET /evaluaciones/?curso={id}&modulo={id} — evaluaciones disponibles."""
    serializer_class = EvaluacionColaboradorSerializer

    def get_queryset(self):
        qs = Evaluacion.objects.select_related('tipo').filter(activo=True)
        curso = self.request.query_params.get('curso')
        modulo = self.request.query_params.get('modulo')
        if curso:
            qs = qs.filter(curso_id=curso)
        if modulo:
            qs = qs.filter(modulo_id=modulo)
        return qs


class PreguntaColaboradorViewSet(_BaseReadOnlyViewSet):
    """GET /preguntas/?evaluacion={id} — preguntas con opciones (sin es_correcta)."""
    serializer_class = PreguntaColaboradorSerializer

    def get_queryset(self):
        qs = Pregunta.objects.prefetch_related('opciones').filter(activo=True)
        evaluacion = self.request.query_params.get('evaluacion')
        if evaluacion:
            qs = qs.filter(evaluacion_id=evaluacion)
        return qs
