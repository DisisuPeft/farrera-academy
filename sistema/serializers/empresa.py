from rest_framework import serializers
from sistema.models import Empresa, Dependencia


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = (
            'id', 'razon_social', 'slug', 'logo',
            'sitio_web', 'telefono', 'email_contacto',
            'direccion', 'rfc', 'status',
        )


class DependenciaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source='empresa.razon_social', read_only=True)

    class Meta:
        model = Dependencia
        fields = (
            'id', 'nombre', 'empresa', 'empresa_nombre',
            'logo', 'sitio_web', 'telefono',
            'email_contacto', 'direccion', 'status',
        )
