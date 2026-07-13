from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CompetenciaViewSet,
    CompetenciaCursoViewSet,
    CompetenciaPuestoViewSet,
    RutaAprendizajeViewSet,
    RutaAprendizajeCursoViewSet,
    CompetenciaColaboradorViewSet,
    MiPerfilCompetenciasView,
    MiInscripcionRutaPerfil
)

router = DefaultRouter()
router.register(r'competencias', CompetenciaViewSet, basename='competencia')
router.register(r'competencias-cursos', CompetenciaCursoViewSet, basename='competencia-curso')
router.register(r'competencias-puestos', CompetenciaPuestoViewSet, basename='competencia-puesto')
router.register(r'rutas-aprendizaje', RutaAprendizajeViewSet, basename='ruta-aprendizaje')
router.register(r'rutas-aprendizaje-cursos', RutaAprendizajeCursoViewSet, basename='ruta-aprendizaje-curso')
router.register(r'competencias-colaborador', CompetenciaColaboradorViewSet, basename='competencia-colaborador')

urlpatterns = [
    path('competencias/', include(router.urls)),
    path('competencias/mi-perfil/', MiPerfilCompetenciasView.as_view(), name='mi-perfil-competencias'),
    path('competencias/iniciar-ruta/', MiInscripcionRutaPerfil.as_view(), name='ruta-inscripcion-perfil')
]
