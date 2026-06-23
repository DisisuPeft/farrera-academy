from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from user.permission import HasRoleWithRoles
from user.authenticate import CustomJWTAuthentication
from catalogos.models import (
    Genero,
    EstadoPais,
    Localidad,
    CatalogStatus,
    TipoBloqueContenido,
    TipeTema,
    TipoEvaluacion,
    NivelCompetencia,
)
from .serializers import (
    GeneroSerializer,
    EstadoPaisSerializer,
    LocalidadSerializer,
    CatalogStatusSerializer,
    TipoBloqueContenidoSerializer,
    TipeTemaSerializer,
    TipoEvaluacionSerializer,
    NivelCompetenciaSerializer,
)


class _BaseCatalogoViewSet(ModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, HasRoleWithRoles(['Administrador'])]


class GeneroViewSet(_BaseCatalogoViewSet):
    queryset = Genero.objects.all()
    serializer_class = GeneroSerializer


class EstadoPaisViewSet(_BaseCatalogoViewSet):
    queryset = EstadoPais.objects.all()
    serializer_class = EstadoPaisSerializer


class LocalidadViewSet(_BaseCatalogoViewSet):
    queryset = Localidad.objects.select_related('country').all()
    serializer_class = LocalidadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(country_id=estado)
        return qs


class CatalogStatusViewSet(_BaseCatalogoViewSet):
    queryset = CatalogStatus.objects.all()
    serializer_class = CatalogStatusSerializer


class TipoBloqueContenidoViewSet(_BaseCatalogoViewSet):
    queryset = TipoBloqueContenido.objects.all()
    serializer_class = TipoBloqueContenidoSerializer


class TipeTemaViewSet(_BaseCatalogoViewSet):
    queryset = TipeTema.objects.all()
    serializer_class = TipeTemaSerializer


class TipoEvaluacionViewSet(_BaseCatalogoViewSet):
    queryset = TipoEvaluacion.objects.all()
    serializer_class = TipoEvaluacionSerializer


class NivelCompetenciaViewSet(_BaseCatalogoViewSet):
    queryset = NivelCompetencia.objects.all()
    serializer_class = NivelCompetenciaSerializer
