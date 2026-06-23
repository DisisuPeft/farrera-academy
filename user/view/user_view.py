from rest_framework import status, viewsets
from user.permission import EsAutorORolPermitido, HasRoleWithRoles
from rest_framework.permissions import IsAuthenticated
from user.authenticate import CustomJWTAuthentication
from rest_framework.response import Response
from user.models import UserCustomize as User
from user.serializers import UserSerializer, RoleSerializer
from user.models import Role
from django.shortcuts import get_object_or_404

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRoleWithRoles(["Administrador"])]
    queryset = User.objects.all()
    authentication_classes = [CustomJWTAuthentication]
    serializer_class = UserSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        qs = qs.exclude(email=user.email)

        return qs


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("Usuario creado con exito.", status=status.HTTP_201_CREATED)


    def update(self, request, *args, **kwargs):
        # partial = kwargs.pop("partial", False)        
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response("Usuario editado con exito", status=status.HTTP_200_OK)
    
    
class RoleModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRoleWithRoles(["Administrador"])]
    queryset = Role.objects.all()
    authentication_classes = [CustomJWTAuthentication]
    serializer_class = RoleSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.exclude(nombre__in=["Colaborador"])
        return qs