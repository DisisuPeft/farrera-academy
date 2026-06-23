from rest_framework import serializers
from sistema.models import Departamento, Puesto


class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ('id', 'nombre', 'codigo', 'descripcion', 'activo', 'creado_at', 'actualizado_at')
        read_only_fields = ('creado_at', 'actualizado_at')


class PuestoSerializer(serializers.ModelSerializer):
    departamento_nombre = serializers.CharField(source='departamento.nombre', read_only=True)

    class Meta:
        model = Puesto
        fields = (
            'id', 'departamento', 'departamento_nombre',
            'nombre', 'codigo', 'descripcion',
            'activo', 'creado_at', 'actualizado_at',
        )
        read_only_fields = ('creado_at', 'actualizado_at')
