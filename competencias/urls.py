from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CompetenciaViewSet, CompetenciaCursoViewSet, CompetenciaPuestoViewSet

router = DefaultRouter()
router.register(r'competencias', CompetenciaViewSet, basename='competencia')
router.register(r'competencias-cursos', CompetenciaCursoViewSet, basename='competencia-curso')
router.register(r'competencias-puestos', CompetenciaPuestoViewSet, basename='competencia-puesto')

urlpatterns = [
    path('competencias/', include(router.urls)),
]
