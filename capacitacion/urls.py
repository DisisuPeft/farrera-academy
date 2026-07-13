from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CursoViewSet,
    ModuloViewSet,
    TemaViewSet,
    ContenidoBloqueViewSet,
    EvaluacionViewSet,
    PreguntaViewSet,
    OpcionPreguntaViewSet,
    InscripcionViewSet,
    ProgresoTemaViewSet,
    ResultadoEvaluacionViewSet,
    VideoStreamView,
)
from .views_colaborador import (
    MisInscripcionesViewSet,
    MisProgresosViewSet,
    MisResultadosViewSet,
    CursoColaboradorViewSet,
    MisCursosViewSet,
    ModuloColaboradorViewSet,
    TemaColaboradorViewSet,
    ContenidoBloqueColaboradorViewSet,
    EvaluacionColaboradorViewSet,
    PreguntaColaboradorViewSet,
)

# --- Admin: acceso solo para Administrador, sin filtro de usuario ---
admin_router = DefaultRouter()
admin_router.register(r'cursos', CursoViewSet, basename='curso')
admin_router.register(r'modulos', ModuloViewSet, basename='modulo-curso')
admin_router.register(r'temas', TemaViewSet, basename='tema')
admin_router.register(r'bloques', ContenidoBloqueViewSet, basename='bloque')
admin_router.register(r'evaluaciones', EvaluacionViewSet, basename='evaluacion')
admin_router.register(r'preguntas', PreguntaViewSet, basename='pregunta')
admin_router.register(r'opciones', OpcionPreguntaViewSet, basename='opcion')
admin_router.register(r'inscripciones', InscripcionViewSet, basename='inscripcion')
admin_router.register(r'progresos-tema', ProgresoTemaViewSet, basename='progreso-tema')
admin_router.register(r'resultados-evaluacion', ResultadoEvaluacionViewSet, basename='resultado-evaluacion')

# --- Colaborador: datos propios (sin conflicto con admin) ---
mis_router = DefaultRouter()
mis_router.register(r'mis-inscripciones', MisInscripcionesViewSet, basename='mis-inscripciones')
mis_router.register(r'mis-progresos', MisProgresosViewSet, basename='mis-progresos')
mis_router.register(r'mis-resultados', MisResultadosViewSet, basename='mis-resultados')
mis_router.register(r'mis-cursos', MisCursosViewSet, basename='mis-cursos')

# --- Colaborador: contenido de lectura (prefijo /ver/ para no colisionar con admin) ---
ver_router = DefaultRouter()
ver_router.register(r'cursos', CursoColaboradorViewSet, basename='cursos-colaborador')
ver_router.register(r'modulos', ModuloColaboradorViewSet, basename='modulos-colaborador')
ver_router.register(r'temas', TemaColaboradorViewSet, basename='temas-colaborador')
ver_router.register(r'bloques', ContenidoBloqueColaboradorViewSet, basename='bloques-colaborador')
ver_router.register(r'evaluaciones', EvaluacionColaboradorViewSet, basename='evaluaciones-colaborador')
ver_router.register(r'preguntas', PreguntaColaboradorViewSet, basename='preguntas-colaborador')

urlpatterns = [
    path('capacitacion/', include(admin_router.urls)),
    path('capacitacion/', include(mis_router.urls)),
    path('capacitacion/ver/', include(ver_router.urls)),
    path('capacitacion/stream/<int:bloque_id>/', VideoStreamView.as_view(), name='video-stream'),
]
