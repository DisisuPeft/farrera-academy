from user.models import UserCustomize as User
from user.models import Role
from rest_framework import serializers
from django.db import transaction
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import exceptions
from catalogos.models import Genero
from rest_framework.validators import ValidationError
from django.shortcuts import get_object_or_404

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'num_colab'

    def validate(self, attrs):
        credentials = {
            'num_colab': attrs.get('num_colab'),
            'password': attrs.get('password')
        }
        user = authenticate(**credentials)

        if user: 
            if user.status == 0:
                raise exceptions.AuthenticationFailed('User is deactivated')

        return super().validate(attrs)

class MeSerializer(serializers.ModelSerializer):
    modulos_accesibles = serializers.SerializerMethodField()
    # pestanias_accesibles = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ("uuid","email", 'nombre_completo', 'modulos_accesibles')
        
    def get_nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellido_paterno} {obj.apellido_materno}" if obj.nombre and obj.apellido_paterno or obj.apellido_materno else ""
        
    def get_modulos_accesibles(self, obj):
        from sistema.serializers import ModulosSerializer
        
        data = obj.modulos_accesibles()

        return ModulosSerializer(data, many=True).data

    # def get_pestanias_accesibles(self, obj):
    #     from sistema.serializers import PestianiaSerializer
        
    #     data = obj.pestanias_accesibles()

    #     return PestianiaSerializer(data, many=True).data



class UserSerializer(serializers.ModelSerializer):
    genero_name = serializers.SerializerMethodField()
    roles_list = serializers.SerializerMethodField()
    puesto_nombre = serializers.CharField(source='puesto.nombre', read_only=True)
    departamento_nombre = serializers.CharField(source='puesto.departamento.nombre', read_only=True)
    dependencia_nombre = serializers.CharField(source='dependencia.nombre', read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance is None:
            self.fields['password'].required = True
        else:
            self.fields['password'].required = False
            self.fields['password'].allow_blank = False

    class Meta:
        model = User
        fields = (
            'uuid', 'num_colab', 'email', 'password',
            'nombre', 'apellido_paterno', 'apellido_materno',
            'genero', 'genero_name', 'edad', 'fecha_nacimiento', 'telefono',
            'curp', 'rfc', 'fecha_alta',
            'puesto', 'puesto_nombre', 'departamento_nombre',
            'dependencia', 'dependencia_nombre',
            'status', 'roles', 'roles_list',
        )
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        roles = validated_data.pop('roles', [])
        password = validated_data.pop('password', None)

        user = User.objects.create_user(password=password, **validated_data)

        if not roles:
            raise ValidationError('Se debe proporcionar un rol al usuario.')

        user.roles.set(roles)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        roles_list = validated_data.pop('roles', None)
        ins = super().update(instance, validated_data)

        if password and len(password) > 6:
            ins.set_password(password)

        if roles_list is not None:
            ins.roles.set(roles_list)

        ins.save()
        return ins

    def get_genero_name(self, obj):
        return obj.genero.nombre if obj.genero else None

    def get_roles_list(self, obj):
        return RoleSerializer(obj.roles.all(), many=True).data


class RoleSerializer(serializers.ModelSerializer):
    permission_detail = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ('id', 'nombre', 'nivel_acceso', 'permission', 'permission_detail')
        extra_kwargs = {
            'permission': {'write_only': True},
        }

    def get_permission_detail(self, obj):
        from sistema.serializers import PermisoSerializer
        return PermisoSerializer(obj.permission.select_related('content_type').all(), many=True).data


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("uuid", "nombre", "apellido_paterno", "apellido_materno", "genero", "edad",
              "fecha_nacimiento", "telefono", "email", "status")