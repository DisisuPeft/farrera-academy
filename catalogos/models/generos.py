from common.models import Base
from django.db import models


class Genero(Base):
    nombre = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        default_permissions = ()