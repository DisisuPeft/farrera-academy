from django.db import models
from common.models import Base, BaseModel, SoftDeleteModel
from django.contrib.auth.models import Permission
import uuid


class Empresa(Base):
    razon_social = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.CharField(max_length=255, blank=True, null=True)
    sitio_web = models.URLField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email_contacto = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    rfc = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        default_permissions = ()
        permissions = [
            ('ver_empresa', 'Ver empresa'),
            ('agregar_empresa', 'Agregar empresa'),
            ('editar_empresa', 'Editar empresa'),
            ('eliminar_empresa', 'Eliminar empresa'),
        ]


class Dependencia(Base):
    nombre = models.CharField(max_length=50)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="dependencia")
    logo = models.CharField(max_length=255, blank=True, null=True)
    sitio_web = models.URLField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email_contacto = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        default_permissions = ()
        permissions = [
            ('ver_dependencia', 'Ver dependencia'),
            ('agregar_dependencia', 'Agregar dependencia'),
            ('editar_dependencia', 'Editar dependencia'),
            ('eliminar_dependencia', 'Eliminar dependencia'),
        ]


# NAVEGACION
# El menú NO autoriza, solo refleja.
# La seguridad vive fuera de la navegación.
#
# SEGURIDAD       → roles, permisos, ownership
# NAVEGACIÓN      → módulos, pestañas
# PREFERENCIA UX  → ocultar, ordenar, fijar
#
# Cada pestaña corresponde a un permiso, no a un rol.
#
# Regla de oro: si un elemento del menú requiere lógica de seguridad, eso NO es UI.
# Y su complemento: si algo es solo visual, jamás debe decidir permisos.

class Modulo(Base):
    nombre = models.CharField(max_length=50)
    icon_path = models.CharField(max_length=50, null=True, blank=True)
    icon = models.CharField(max_length=50, null=True, blank=True)
    bgColor = models.CharField(max_length=20, null=True, blank=True)
    textColor = models.CharField(max_length=20, null=True, blank=True)
    href = models.CharField(max_length=50, null=True, blank=True)
    orden = models.IntegerField(blank=True, null=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['orden']
        default_permissions = ()


class Pestania(Base):
    nombre = models.CharField(max_length=50)
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name="pestanias")
    href = models.CharField(max_length=50, null=True, blank=True)
    icon = models.CharField(max_length=50, null=True, blank=True)
    icon_path = models.CharField(max_length=50, null=True, blank=True)
    orden = models.IntegerField(null=True, blank=True)
    permission = models.ManyToManyField(Permission, related_name="pestanias", blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['orden']
        default_permissions = ()


# ORGANIZACIÓN

class Departamento(BaseModel, SoftDeleteModel):
    nombre = models.CharField(max_length=120)
    codigo = models.SlugField(unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        default_permissions = ()
        permissions = [
            ('ver_departamento', 'Ver departamento'),
            ('agregar_departamento', 'Agregar departamento'),
            ('editar_departamento', 'Editar departamento'),
            ('eliminar_departamento', 'Eliminar departamento'),
        ]

    def __str__(self):
        return self.nombre


class Puesto(BaseModel, SoftDeleteModel):
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='puestos',
    )
    nombre = models.CharField(max_length=120)
    codigo = models.SlugField()
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ['departamento', 'nombre']
        verbose_name = 'Puesto'
        verbose_name_plural = 'Puestos'
        unique_together = [('departamento', 'codigo')]
        default_permissions = ()
        permissions = [
            ('ver_puesto', 'Ver puesto'),
            ('agregar_puesto', 'Agregar puesto'),
            ('editar_puesto', 'Editar puesto'),
            ('eliminar_puesto', 'Eliminar puesto'),
        ]

    def __str__(self):
        return f'{self.departamento} — {self.nombre}'
