from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated

from user.authenticate import CustomJWTAuthentication

from capacitacion.models import (
    Inscripcion, ProgresoTema, ResultadoEvaluacion,
    Curso, Modulo, Tema, ContenidoBloque,
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
    EvaluacionColaboradorSerializer,
    PreguntaColaboradorSerializer,
)


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
    PATCH /mis-inscripciones/{id}/    → marcar curso como completado { "completado_at": "..." }
    """
    serializer_class = MiInscripcionSerializer

    def get_queryset(self):
        return (
            Inscripcion.objects
            .select_related('curso')
            .filter(colaborador=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(colaborador=self.request.user)


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
            .filter(colaborador=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(colaborador=self.request.user)


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
            .filter(colaborador=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(colaborador=self.request.user)


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
        qs = ContenidoBloque.objects.select_related('tipo').filter(activo=True)
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
