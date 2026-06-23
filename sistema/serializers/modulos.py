from rest_framework import serializers
from django.contrib.auth.models import Permission
from sistema.models import Modulo, Pestania


class PermisoSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source='content_type.app_label', read_only=True)

    class Meta:
        model = Permission
        fields = ('id', 'name', 'codename', 'app_label')


# Serializer ligero para el sidebar del usuario final
class PestianiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pestania
        fields = ('uuid', 'nombre', 'href', 'icon', 'icon_path', 'orden')


# Serializer completo para administración
class PestaniaAdminSerializer(serializers.ModelSerializer):
    permission_detail = PermisoSerializer(source='permission', many=True, read_only=True)

    class Meta:
        model = Pestania
        fields = (
            'id', 'uuid', 'nombre', 'modulo',
            'href', 'icon', 'icon_path', 'orden',
            'permission', 'permission_detail', 'status',
        )


# Serializer ligero para el sidebar del usuario final
class ModulosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = ('uuid', 'href', 'bgColor', 'textColor', 'icon', 'icon_path', 'nombre', 'orden')


# Serializer completo para administración, con pestañas anidadas
class ModuloAdminSerializer(serializers.ModelSerializer):
    pestanias = PestianiaSerializer(many=True, read_only=True)

    class Meta:
        model = Modulo
        fields = (
            'id', 'uuid', 'nombre',
            'icon_path', 'icon', 'bgColor', 'textColor',
            'href', 'orden', 'pestanias', 'status',
        )
