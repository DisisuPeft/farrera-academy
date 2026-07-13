from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from user.authenticate import CustomJWTAuthentication
from user.permission import HasRoleWithRoles

from capacitacion.models import (
    Curso, Modulo, Tema, ContenidoBloque,
    Evaluacion, Pregunta, OpcionPregunta,
    Inscripcion, ProgresoTema, ResultadoEvaluacion,
)
from capacitacion.serializers import (
    CursoSerializer, ModuloSerializer, TemaSerializer, ContenidoBloqueSerializer,
    EvaluacionSerializer, PreguntaSerializer, OpcionPreguntaSerializer,
    InscripcionSerializer, ProgresoTemaSerializer, ResultadoEvaluacionSerializer,
)


class _BaseAdminViewSet(ModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, HasRoleWithRoles(['Administrador'])]


# ---------------------------------------------------------------------------
# Estructura del curso
# ---------------------------------------------------------------------------

class CursoViewSet(_BaseAdminViewSet):
    queryset = Curso.objects.select_related('status').all()
    serializer_class = CursoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_id = self.request.query_params.get('status')
        if status_id:
            qs = qs.filter(status_id=status_id)
        return qs


class ModuloViewSet(_BaseAdminViewSet):
    queryset = Modulo.objects.select_related('curso').all()
    serializer_class = ModuloSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        curso = self.request.query_params.get('curso')
        if curso:
            qs = qs.filter(curso_id=curso)
        return qs


class TemaViewSet(_BaseAdminViewSet):
    queryset = Tema.objects.select_related('modulo', 'tipo').all()
    serializer_class = TemaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        modulo = self.request.query_params.get('modulo')
        if modulo:
            qs = qs.filter(modulo_id=modulo)
        return qs


class ContenidoBloqueViewSet(_BaseAdminViewSet):
    queryset = ContenidoBloque.objects.select_related('tema', 'tipo').all()
    serializer_class = ContenidoBloqueSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        tema = self.request.query_params.get('tema')
        if tema:
            qs = qs.filter(tema_id=tema)
        return qs


# ---------------------------------------------------------------------------
# Evaluaciones
# ---------------------------------------------------------------------------

class EvaluacionViewSet(_BaseAdminViewSet):
    queryset = Evaluacion.objects.select_related('tipo', 'curso', 'modulo').all()
    serializer_class = EvaluacionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        curso = self.request.query_params.get('curso')
        modulo = self.request.query_params.get('modulo')
        if curso:
            qs = qs.filter(curso_id=curso)
        if modulo:
            qs = qs.filter(modulo_id=modulo)
        return qs


class PreguntaViewSet(_BaseAdminViewSet):
    queryset = Pregunta.objects.select_related('evaluacion').all()
    serializer_class = PreguntaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        evaluacion = self.request.query_params.get('evaluacion')
        if evaluacion:
            qs = qs.filter(evaluacion_id=evaluacion)
        return qs


class OpcionPreguntaViewSet(_BaseAdminViewSet):
    queryset = OpcionPregunta.objects.select_related('pregunta').all()
    serializer_class = OpcionPreguntaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        pregunta = self.request.query_params.get('pregunta')
        if pregunta:
            qs = qs.filter(pregunta_id=pregunta)
        return qs


# ---------------------------------------------------------------------------
# Progreso y participación
# ---------------------------------------------------------------------------

class InscripcionViewSet(_BaseAdminViewSet):
    queryset = Inscripcion.objects.select_related('colaborador', 'curso').all()
    serializer_class = InscripcionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        curso = self.request.query_params.get('curso')
        colaborador = self.request.query_params.get('colaborador')
        if curso:
            qs = qs.filter(curso_id=curso)
        if colaborador:
            qs = qs.filter(colaborador_id=colaborador)
        return qs


class ProgresoTemaViewSet(_BaseAdminViewSet):
    queryset = ProgresoTema.objects.select_related('colaborador', 'tema').all()
    serializer_class = ProgresoTemaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        tema = self.request.query_params.get('tema')
        colaborador = self.request.query_params.get('colaborador')
        if tema:
            qs = qs.filter(tema_id=tema)
        if colaborador:
            qs = qs.filter(colaborador_id=colaborador)
        return qs


class ResultadoEvaluacionViewSet(_BaseAdminViewSet):
    queryset = ResultadoEvaluacion.objects.select_related('colaborador', 'evaluacion').all()
    serializer_class = ResultadoEvaluacionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        evaluacion = self.request.query_params.get('evaluacion')
        colaborador = self.request.query_params.get('colaborador')
        if evaluacion:
            qs = qs.filter(evaluacion_id=evaluacion)
        if colaborador:
            qs = qs.filter(colaborador_id=colaborador)
        return qs


# ---------------------------------------------------------------------------
# Stream de video
# ---------------------------------------------------------------------------

class VideoStreamView(APIView):
    """
    Valida el JWT y sirve el video via X-Accel-Redirect (nginx en producción).
    En local (DEBUG=True) redirige directamente a la URL del archivo.
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, bloque_id):
        bloque = get_object_or_404(ContenidoBloque, pk=bloque_id, activo=True)

        if not bloque.video_archivo:
            return Response(
                {'detail': 'Este bloque no tiene video.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if settings.DEBUG:
            return FileResponse(bloque.video_archivo.open('rb'), content_type='video/mp4')

        response = HttpResponse(content_type='video/mp4')
        response['X-Accel-Redirect'] = f'/media/{bloque.video_archivo.name}'
        response['Content-Disposition'] = 'inline'
        return response
