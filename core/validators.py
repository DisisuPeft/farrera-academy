from rest_framework import serializers

def validate_owner_in_department(owner, department):
    if owner and department:
        if not owner.departments.filter(pk=department.pk).exists():
            raise serializers.ValidationError("El usuario no pertenece a este departamento")