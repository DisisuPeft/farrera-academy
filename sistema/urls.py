from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    EmpresaViewSet,
    DependenciaViewSet,
    ModuloViewSet,
    PestaniaViewSet,
    DepartamentoViewSet,
    PuestoViewSet,
    GetModulosUsuario,
    GetPestaniaUsuario,
    PermisosDisponiblesView,
)

router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet, basename='empresa')
router.register(r'dependencias', DependenciaViewSet, basename='dependencia')
router.register(r'modulos', ModuloViewSet, basename='modulo')
router.register(r'pestanias', PestaniaViewSet, basename='pestania')
router.register(r'departamentos', DepartamentoViewSet, basename='departamento')
router.register(r'puestos', PuestoViewSet, basename='puesto')

urlpatterns = [
    path('sistema/', include(router.urls)),
    # Sidebar
    path('sistema/sidebar/modulos/', GetModulosUsuario.as_view(), name='sidebar-modulos'),
    path('sistema/sidebar/pestanias/', GetPestaniaUsuario.as_view(), name='sidebar-pestanias'),
    # Utilidades
    path('sistema/permisos/', PermisosDisponiblesView.as_view(), name='permisos-disponibles'),
]
