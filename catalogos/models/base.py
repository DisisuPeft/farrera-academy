from django.db import models
from common.models import BaseModel


class BaseCatalogo(BaseModel):
    nombre = models.CharField(max_length=120)
    codigo = models.SlugField(unique=True)
    icono = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=20, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ['orden', 'nombre']
        default_permissions = ()

    def __str__(self):
        return f'{self.nombre} ({self.codigo})'
