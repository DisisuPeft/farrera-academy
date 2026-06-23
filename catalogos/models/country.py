from django.db import models
from common.models import Base


class EstadoPais(Base):
    name = models.CharField(max_length=100)

    class Meta:
        default_permissions = ()


class Localidad(Base):
    country = models.ForeignKey(EstadoPais, on_delete=models.CASCADE, related_name="cities")
    name = models.CharField(max_length=100)
    clave = models.CharField(max_length=100)

    class Meta:
        default_permissions = ()
