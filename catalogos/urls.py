from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GeneroViewSet,
    EstadoPaisViewSet,
    LocalidadViewSet,
    CatalogStatusViewSet,
    TipoBloqueContenidoViewSet,
    TipeTemaViewSet,
    TipoEvaluacionViewSet,
    NivelCompetenciaViewSet,
)

router = DefaultRouter()
router.register(r'generos', GeneroViewSet, basename='genero')
router.register(r'estados', EstadoPaisViewSet, basename='estado')
router.register(r'localidades', LocalidadViewSet, basename='localidad')
router.register(r'status', CatalogStatusViewSet, basename='catalog-status')
router.register(r'tipos-bloque', TipoBloqueContenidoViewSet, basename='tipo-bloque')
router.register(r'tipos-tema', TipeTemaViewSet, basename='tipo-tema')
router.register(r'tipos-evaluacion', TipoEvaluacionViewSet, basename='tipo-evaluacion')
router.register(r'niveles-competencia', NivelCompetenciaViewSet, basename='nivel-competencia')

urlpatterns = [
    path('catalogos/', include(router.urls)),
]
