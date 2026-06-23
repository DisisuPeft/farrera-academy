from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from user.authenticate import CustomJWTAuthentication
from user.permission import HasRoleWithRoles

from competencias.models import Competencia, CompetenciaCurso, CompetenciaPuesto
from competencias.serializers import (
    CompetenciaSerializer,
    CompetenciaCursoSerializer,
    CompetenciaPuestoSerializer,
)


class _BaseAdminViewSet(ModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, HasRoleWithRoles(['Administrador'])]


class _BaseSoftDeleteViewSet(_BaseAdminViewSet):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompetenciaViewSet(_BaseSoftDeleteViewSet):
    queryset = Competencia.objects.all()
    serializer_class = CompetenciaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        codigo = self.request.query_params.get('codigo')
        if codigo:
            qs = qs.filter(codigo=codigo)
        return qs


class CompetenciaCursoViewSet(_BaseSoftDeleteViewSet):
    queryset = CompetenciaCurso.objects.select_related(
        'competencia', 'curso', 'nivel'
    ).all()
    serializer_class = CompetenciaCursoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        competencia = self.request.query_params.get('competencia')
        curso = self.request.query_params.get('curso')
        if competencia:
            qs = qs.filter(competencia_id=competencia)
        if curso:
            qs = qs.filter(curso_id=curso)
        return qs


class CompetenciaPuestoViewSet(_BaseSoftDeleteViewSet):
    queryset = CompetenciaPuesto.objects.select_related(
        'competencia', 'puesto', 'nivel'
    ).all()
    serializer_class = CompetenciaPuestoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        competencia = self.request.query_params.get('competencia')
        puesto = self.request.query_params.get('puesto')
        if competencia:
            qs = qs.filter(competencia_id=competencia)
        if puesto:
            qs = qs.filter(puesto_id=puesto)
        return qs
