from .curso import CursoSerializer, ModuloSerializer, TemaSerializer, ContenidoBloqueSerializer
from .evaluacion import EvaluacionSerializer, PreguntaSerializer, OpcionPreguntaSerializer
from .progreso import InscripcionSerializer, ProgresoTemaSerializer, ResultadoEvaluacionSerializer
from .colaborador import (
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

__all__ = [
    'CursoSerializer',
    'ModuloSerializer',
    'TemaSerializer',
    'ContenidoBloqueSerializer',
    'EvaluacionSerializer',
    'PreguntaSerializer',
    'OpcionPreguntaSerializer',
    'InscripcionSerializer',
    'ProgresoTemaSerializer',
    'ResultadoEvaluacionSerializer',
    'MiInscripcionSerializer',
    'MiProgresoTemaSerializer',
    'MiResultadoEvaluacionSerializer',
    'CursoColaboradorSerializer',
    'ModuloColaboradorSerializer',
    'TemaColaboradorSerializer',
    'ContenidoBloqueColaboradorSerializer',
    'EvaluacionColaboradorSerializer',
    'PreguntaColaboradorSerializer',
]
