from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import Permission

from user.authenticate import CustomJWTAuthentication
from user.permission import HasRoleWithRoles

from sistema.models import Empresa, Dependencia, Modulo, Pestania, Departamento, Puesto
from sistema.serializers import (
    EmpresaSerializer,
    DependenciaSerializer,
    PestianiaSerializer,
    PestaniaAdminSerializer,
    ModulosSerializer,
    ModuloAdminSerializer,
    PermisoSerializer,
    DepartamentoSerializer,
    PuestoSerializer,
)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class _BaseAdminViewSet(ModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, HasRoleWithRoles(['Administrador'])]


class _BaseSoftDeleteViewSet(_BaseAdminViewSet):
    """ViewSet base para modelos con SoftDeleteModel.
    Filtra eliminados y sobrescribe destroy para soft-delete."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Empresa
# ---------------------------------------------------------------------------

class EmpresaViewSet(_BaseAdminViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        slug = self.request.query_params.get('slug')
        if slug:
            qs = qs.filter(slug=slug)
        return qs


# ---------------------------------------------------------------------------
# Dependencia
# ---------------------------------------------------------------------------

class DependenciaViewSet(_BaseAdminViewSet):
    queryset = Dependencia.objects.select_related('empresa').all()
    serializer_class = DependenciaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        empresa = self.request.query_params.get('empresa')
        if empresa:
            qs = qs.filter(empresa_id=empresa)
        return qs


# ---------------------------------------------------------------------------
# Módulos y Pestañas (navegación)
# ---------------------------------------------------------------------------

class ModuloViewSet(_BaseAdminViewSet):
    queryset = Modulo.objects.prefetch_related('pestanias').all()
    serializer_class = ModuloAdminSerializer


class PestaniaViewSet(_BaseAdminViewSet):
    queryset = Pestania.objects.select_related('modulo').prefetch_related('permission__content_type').all()
    serializer_class = PestaniaAdminSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        modulo = self.request.query_params.get('modulo')
        if modulo:
            qs = qs.filter(modulo_id=modulo)
        return qs


# ---------------------------------------------------------------------------
# Sidebar (usuario final)
# ---------------------------------------------------------------------------

class GetModulosUsuario(APIView):
    """Devuelve los módulos accesibles para el usuario autenticado."""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        modulos = request.user.modulos_accesibles()
        serializer = ModulosSerializer(modulos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetPestaniaUsuario(APIView):
    """Devuelve las pestañas de un módulo accesibles para el usuario autenticado."""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        modulo_uuid = request.query_params.get('ref')
        pestanias = request.user.pestanias_accesibles(modulo_uuid)
        serializer = PestianiaSerializer(pestanias, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Organización
# ---------------------------------------------------------------------------

class DepartamentoViewSet(_BaseSoftDeleteViewSet):
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer


class PuestoViewSet(_BaseSoftDeleteViewSet):
    queryset = Puesto.objects.select_related('departamento').all()
    serializer_class = PuestoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        departamento = self.request.query_params.get('departamento')
        if departamento:
            qs = qs.filter(departamento_id=departamento)
        return qs


# ---------------------------------------------------------------------------
# Permisos disponibles (para asignar a Roles y Pestañas)
# ---------------------------------------------------------------------------

class PermisosDisponiblesView(APIView):
    """Lista todos los permisos custom del sistema (en español).
    Excluye los permisos internos de Django (admin, auth, contenttypes, sessions)."""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, HasRoleWithRoles(['Administrador'])]

    APPS_INTERNAS = {'admin', 'auth', 'contenttypes', 'sessions', 'authtoken', 'token_blacklist'}

    def get(self, request):
        permisos = (
            Permission.objects
            .select_related('content_type')
            .exclude(content_type__app_label__in=self.APPS_INTERNAS)
            .order_by('content_type__app_label', 'codename')
        )
        app = request.query_params.get('app')
        if app:
            permisos = permisos.filter(content_type__app_label=app)

        serializer = PermisoSerializer(permisos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
