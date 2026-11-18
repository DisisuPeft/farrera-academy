from django.conf import settings
from django.db import models, transaction
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from user.authenticate import CustomJWTAuthentication
from user.permission import HasRoleWithRoles

from capacitacion.models import (
    Curso, Modulo, Tema, ContenidoBloque, ContenidoBloqueItem,
    ContenidoBloqueArchivo, ContenidoBloqueOpcion,
    Evaluacion, Pregunta, OpcionPregunta,
    Inscripcion, ProgresoTema, ResultadoEvaluacion,
)
from capacitacion.serializers import (
    CursoSerializer, ModuloSerializer, TemaSerializer, ContenidoBloqueSerializer,
    ContenidoBloqueItemSerializer, ContenidoBloqueArchivoSerializer, ContenidoBloqueOpcionSerializer,
    EvaluacionSerializer, PreguntaSerializer, OpcionPreguntaSerializer,
    InscripcionSerializer, ProgresoTemaSerializer, ResultadoEvaluacionSerializer,
)
from capacitacion.services.finalizacion_service import FinalizacionService, YaFinalizada


def _scope_por_empresa(queryset, user, prefijo_curso=''):
    """
    Ámbito de autorización (ownership): un Administrador que no es superusuario
    solo ve/edita los cursos de su propia Empresa (via `user.dependencia.empresa`),
    más los cursos "globales" (`empresa=None`, compatibilidad con datos ya
    cargados sin dueño asignado). El superusuario no se filtra.

    `prefijo_curso`: '' si `queryset` es de Curso directamente, o el lookup
    hasta llegar a Curso (ej. 'curso', 'modulo__curso', 'tema__modulo__curso').
    """
    if user.is_superuser:
        return queryset
    campo_empresa = f'{prefijo_curso}__empresa' if prefijo_curso else 'empresa'
    empresa_id = user.dependencia.empresa_id if user.dependencia_id else None
    return queryset.filter(
        models.Q(**{f'{campo_empresa}__isnull': True}) | models.Q(**{f'{campo_empresa}_id': empresa_id})
    )


def _reordenar_en_lote(queryset, orden_data, campo_grupo, grupo_id):
    """
    Aplica un reordenamiento en lote dentro de una transacción atómica.
    `orden_data`: lista de {"id": <pk>, "orden": <int>}.
    `queryset`: queryset base del modelo (ya filtrado por tipo si aplica).
    `campo_grupo`: nombre del FK que agrupa los registros (ej. 'tema_id', 'bloque_id').
    `grupo_id`: valor de ese FK al que deben pertenecer todos los registros recibidos.

    Devuelve (ok: bool, detail: str | None, objetos: dict[id, obj]).
    """
    if not isinstance(orden_data, list) or not orden_data:
        return False, 'Se requiere "orden": una lista de {"id": <id>, "orden": <int>}.', None

    try:
        pares = [(int(item['id']), int(item['orden'])) for item in orden_data]
    except (KeyError, TypeError, ValueError):
        return False, 'Cada elemento de "orden" debe traer "id" y "orden" numéricos.', None

    ids = [pid for pid, _ in pares]
    if len(set(ids)) != len(ids):
        return False, 'Hay ids repetidos en "orden".', None

    ordenes = [o for _, o in pares]
    if len(set(ordenes)) != len(ordenes):
        return False, 'Los valores de "orden" no pueden repetirse.', None

    grupo_qs = queryset.filter(**{campo_grupo: grupo_id})
    objetos = {obj.id: obj for obj in grupo_qs.filter(id__in=ids)}
    if len(objetos) != len(ids):
        return False, 'Alguno de los elementos no existe o no pertenece a ese grupo.', None

    # `orden` es un entero positivo (unique_together con el grupo), así que no se puede usar
    # un valor negativo como escalón temporal. En su lugar, se usa un rango por encima del
    # máximo actual del grupo (incluyendo filas no tocadas por este reordenamiento) para
    # garantizar que ningún valor temporal choque con uno ya existente.
    max_actual = grupo_qs.aggregate(models.Max('orden'))['orden__max'] or 0
    base_temporal = max_actual + 1

    with transaction.atomic():
        for i, (pid, _nuevo_orden) in enumerate(pares):
            obj = objetos[pid]
            obj.orden = base_temporal + i
            obj.save(update_fields=['orden'])
        for pid, nuevo_orden in pares:
            obj = objetos[pid]
            obj.orden = nuevo_orden
            obj.save(update_fields=['orden'])

    return True, None, objetos


class _BaseAdminViewSet(ModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, HasRoleWithRoles(['Administrador'])]


# ---------------------------------------------------------------------------
# Estructura del curso
# ---------------------------------------------------------------------------

class CursoViewSet(_BaseAdminViewSet):
    queryset = Curso.objects.select_related('status', 'empresa').all()
    serializer_class = CursoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _scope_por_empresa(qs, self.request.user)
        status_id = self.request.query_params.get('status')
        if status_id:
            qs = qs.filter(status_id=status_id)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser:
            serializer.save(creado_por=user)
        else:
            empresa = user.dependencia.empresa if user.dependencia_id else None
            serializer.save(empresa=empresa, creado_por=user)

    def perform_update(self, serializer):
        user = self.request.user
        if user.is_superuser:
            serializer.save()
        else:
            # Un Administrador de una empresa no puede reasignar el curso a otra.
            empresa = user.dependencia.empresa if user.dependencia_id else None
            serializer.save(empresa=empresa)


class ModuloViewSet(_BaseAdminViewSet):
    queryset = Modulo.objects.select_related('curso').all()
    serializer_class = ModuloSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _scope_por_empresa(qs, self.request.user, 'curso')
        curso = self.request.query_params.get('curso')
        if curso:
            qs = qs.filter(curso_id=curso)
        return qs

    def destroy(self, _request, *args, **kwargs):
        modulo = self.get_object()
        curso_id = modulo.curso_id
        orden_borrado = modulo.orden
        modulo.delete()
        posteriores = Modulo.objects.filter(
            curso_id=curso_id, orden__gt=orden_borrado,
        ).order_by('orden')
        for m in posteriores:
            m.orden -= 1
            m.save(update_fields=['orden'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TemaViewSet(_BaseAdminViewSet):
    queryset = Tema.objects.select_related('modulo', 'tipo').all()
    serializer_class = TemaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _scope_por_empresa(qs, self.request.user, 'modulo__curso')
        modulo = self.request.query_params.get('modulo')
        if modulo:
            qs = qs.filter(modulo_id=modulo)
        return qs

    def destroy(self, _request, *args, **kwargs):
        tema = self.get_object()
        modulo_id = tema.modulo_id
        orden_borrado = tema.orden
        tema.delete()
        # Cerrar el gap: orden ascendente para no violar unique_together('modulo','orden')
        posteriores = Tema.objects.filter(
            modulo_id=modulo_id, orden__gt=orden_borrado,
        ).order_by('orden')
        for t in posteriores:
            t.orden -= 1
            t.save(update_fields=['orden'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContenidoBloqueViewSet(_BaseAdminViewSet):
    queryset = ContenidoBloque.objects.select_related('tema', 'tipo').prefetch_related('bloque_items').all()
    serializer_class = ContenidoBloqueSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _scope_por_empresa(qs, self.request.user, 'tema__modulo__curso')
        tema = self.request.query_params.get('tema')
        if tema:
            qs = qs.filter(tema_id=tema)
        return qs

    def destroy(self, _request, *args, **kwargs):
        bloque = self.get_object()
        tema_id = bloque.tema_id
        orden_borrado = bloque.orden
        bloque.delete()
        posteriores = ContenidoBloque.objects.filter(
            tema_id=tema_id, orden__gt=orden_borrado,
        ).order_by('orden')
        for b in posteriores:
            b.orden -= 1
            b.save(update_fields=['orden'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['patch'], url_path='reordenar')
    def reordenar(self, request):
        """
        PATCH /capacitacion/bloques/reordenar/
        Body: { "tema": <id>, "orden": [{"id": <id>, "orden": <int>}, ...] }
        Aplica todo el reordenamiento del tema en una sola transacción (todo o nada).
        """
        tema_id = request.data.get('tema')
        if not tema_id:
            return Response({'detail': 'Se requiere "tema".'}, status=status.HTTP_400_BAD_REQUEST)

        ok, detail, _ = _reordenar_en_lote(
            ContenidoBloque.objects.all(), request.data.get('orden'), 'tema_id', tema_id,
        )
        if not ok:
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

        actualizados = ContenidoBloque.objects.filter(tema_id=tema_id).select_related('tipo').order_by('orden')
        serializer = self.get_serializer(actualizados, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ContenidoBloqueItemViewSet(_BaseAdminViewSet):
    queryset = ContenidoBloqueItem.objects.select_related('bloque').all()
    serializer_class = ContenidoBloqueItemSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _scope_por_empresa(qs, self.request.user, 'bloque__tema__modulo__curso')
        bloque = self.request.query_params.get('bloque')
        if bloque:
            qs = qs.filter(bloque_id=bloque)
        return qs

    def destroy(self, _request, *args, **kwargs):
        item = self.get_object()
        bloque_id = item.bloque_id
        orden_borrado = item.orden
        item.delete()
        posteriores = ContenidoBloqueItem.objects.filter(
            bloque_id=bloque_id, orden__gt=orden_borrado,
        ).order_by('orden')
        for i in posteriores:
            i.orden -= 1
            i.save(update_fields=['orden'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['patch'], url_path='reordenar')
    def reordenar(self, request):
        """
        PATCH /capacitacion/bloque-items/reordenar/
        Body: { "bloque": <id>, "orden": [{"id": <id>, "orden": <int>}, ...] }
        """
        bloque_id = request.data.get('bloque')
        if not bloque_id:
            return Response({'detail': 'Se requiere "bloque".'}, status=status.HTTP_400_BAD_REQUEST)

        ok, detail, _ = _reordenar_en_lote(
            ContenidoBloqueItem.objects.all(), request.data.get('orden'), 'bloque_id', bloque_id,
        )
        if not ok:
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

        actualizados = ContenidoBloqueItem.objects.filter(bloque_id=bloque_id).order_by('orden')
        serializer = self.get_serializer(actualizados, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ContenidoBloqueArchivoViewSet(_BaseAdminViewSet):
    """Adjuntos de un bloque (audio, documento, etc.) — reutiliza BaseFileEntity."""
    queryset = ContenidoBloqueArchivo.objects.select_related('bloque').all()
    serializer_class = ContenidoBloqueArchivoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _scope_por_empresa(qs, self.request.user, 'bloque__tema__modulo__curso')
        bloque = self.request.query_params.get('bloque')
        if bloque:
            qs = qs.filter(bloque_id=bloque)
        return qs

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    def destroy(self, _request, *args, **kwargs):
        archivo = self.get_object()
        bloque_id = archivo.bloque_id
        orden_borrado = archivo.orden
        archivo.delete()
        posteriores = ContenidoBloqueArchivo.objects.filter(
            bloque_id=bloque_id, orden__gt=orden_borrado,
        ).order_by('orden')
        for a in posteriores:
            a.orden -= 1
            a.save(update_fields=['orden'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['patch'], url_path='reordenar')
    def reordenar(self, request):
        """
        PATCH /capacitacion/bloque-archivos/reordenar/
        Body: { "bloque": <id>, "orden": [{"id": <id>, "orden": <int>}, ...] }
        """
        bloque_id = request.data.get('bloque')
        if not bloque_id:
            return Response({'detail': 'Se requiere "bloque".'}, status=status.HTTP_400_BAD_REQUEST)

        ok, detail, _ = _reordenar_en_lote(
            ContenidoBloqueArchivo.objects.all(), request.data.get('orden'), 'bloque_id', bloque_id,
        )
        if not ok:
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

        actualizados = ContenidoBloqueArchivo.objects.filter(bloque_id=bloque_id).order_by('orden')
        serializer = self.get_serializer(actualizados, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ContenidoBloqueOpcionViewSet(_BaseAdminViewSet):
    """
    Opciones de un bloque evaluativo embebido ('opcion-multiple'/'verdadero-falso').
    Autoría únicamente: expone `es_correcta`, por eso vive bajo el router admin,
    nunca bajo /ver/ (el colaborador usa ContenidoBloqueOpcionColaboradorSerializer,
    que la excluye).
    """
    queryset = ContenidoBloqueOpcion.objects.select_related('bloque').all()
    serializer_class = ContenidoBloqueOpcionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _scope_por_empresa(qs, self.request.user, 'bloque__tema__modulo__curso')
        bloque = self.request.query_params.get('bloque')
        if bloque:
            qs = qs.filter(bloque_id=bloque)
        return qs

    def destroy(self, _request, *args, **kwargs):
        opcion = self.get_object()
        bloque_id = opcion.bloque_id
        orden_borrado = opcion.orden
        opcion.delete()
        posteriores = ContenidoBloqueOpcion.objects.filter(
            bloque_id=bloque_id, orden__gt=orden_borrado,
        ).order_by('orden')
        for o in posteriores:
            o.orden -= 1
            o.save(update_fields=['orden'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['patch'], url_path='reordenar')
    def reordenar(self, request):
        """
        PATCH /capacitacion/bloque-opciones/reordenar/
        Body: { "bloque": <id>, "orden": [{"id": <id>, "orden": <int>}, ...] }
        """
        bloque_id = request.data.get('bloque')
        if not bloque_id:
            return Response({'detail': 'Se requiere "bloque".'}, status=status.HTTP_400_BAD_REQUEST)

        ok, detail, _ = _reordenar_en_lote(
            ContenidoBloqueOpcion.objects.all(), request.data.get('orden'), 'bloque_id', bloque_id,
        )
        if not ok:
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

        actualizados = ContenidoBloqueOpcion.objects.filter(bloque_id=bloque_id).order_by('orden')
        serializer = self.get_serializer(actualizados, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        qs = _scope_por_empresa(qs, self.request.user, 'curso')
        curso = self.request.query_params.get('curso')
        colaborador = self.request.query_params.get('colaborador')
        if curso:
            qs = qs.filter(curso_id=curso)
        if colaborador:
            qs = qs.filter(colaborador_id=colaborador)
        return qs

    @action(detail=True, methods=['post'])
    def forzar(self, request, pk=None):
        inscripcion = self.get_object()
        resultado = FinalizacionService.forzar(inscripcion, actor=request.user)
        if isinstance(resultado, YaFinalizada):
            return Response({'detail': 'La inscripción ya estaba finalizada.'}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(resultado)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProgresoTemaViewSet(_BaseAdminViewSet):
    queryset = ProgresoTema.objects.select_related('inscripcion__colaborador', 'tema').all()
    serializer_class = ProgresoTemaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _scope_por_empresa(qs, self.request.user, 'inscripcion__curso')
        tema = self.request.query_params.get('tema')
        colaborador = self.request.query_params.get('colaborador')
        if tema:
            qs = qs.filter(tema_id=tema)
        if colaborador:
            qs = qs.filter(inscripcion__colaborador_id=colaborador)
        return qs


class ResultadoEvaluacionViewSet(_BaseAdminViewSet):
    queryset = ResultadoEvaluacion.objects.select_related('inscripcion__colaborador', 'evaluacion').all()
    serializer_class = ResultadoEvaluacionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _scope_por_empresa(qs, self.request.user, 'inscripcion__curso')
        evaluacion = self.request.query_params.get('evaluacion')
        colaborador = self.request.query_params.get('colaborador')
        if evaluacion:
            qs = qs.filter(evaluacion_id=evaluacion)
        if colaborador:
            qs = qs.filter(inscripcion__colaborador_id=colaborador)
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
