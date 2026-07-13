from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db.models.fields.related import ForeignKey
from user.manager import CustomUserManager
from common.models import Base, BaseAcademico
import uuid
from django.utils.timezone import now


class UserCustomize(AbstractUser, Base):
    username = None
    num_colab = models.PositiveIntegerField(unique=True)
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100)
    apellido_materno = models.CharField(max_length=100, blank=True)
    genero = models.ForeignKey("catalogos.Genero", on_delete=models.CASCADE, related_name="users", null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=15, null=True, blank=True)
    puesto = models.ForeignKey('sistema.Puesto', blank=True, null=True, on_delete=models.CASCADE, related_name="users")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    roles = models.ManyToManyField("user.Role", related_name="users", blank=True)
    curp = models.CharField(max_length=18, unique=True)
    rfc = models.CharField(max_length=13, unique=True)
    fecha_alta = models.DateField()
    dependencia = models.ForeignKey("sistema.Dependencia", on_delete=models.PROTECT, related_name="usuarios")
    
    USERNAME_FIELD = 'num_colab'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        default_permissions = ()
        permissions = [
            ('ver_usuario', 'Ver usuario'),
            ('agregar_usuario', 'Agregar usuario'),
            ('editar_usuario', 'Editar usuario'),
            ('eliminar_usuario', 'Eliminar usuario'),
        ]

    def modulos_accesibles(self):
        from sistema.models import Pestania
        from collections import defaultdict

        if self.is_superuser:
            pestanias = Pestania.objects.filter(status=1).select_related("modulo").order_by("modulo__orden", "orden")
        else:
            mis_permisos = self.get_all_permissions()
            pestanias = Pestania.objects.filter(status=1).select_related("modulo").prefetch_related("permission__content_type").order_by("modulo__orden", "orden")
            resultado = []
            for p in pestanias:
                perms_req = {f"{pm.content_type.app_label}.{pm.codename}" for pm in p.permission.all()}
                if not perms_req or (perms_req & mis_permisos):
                    resultado.append(p)
            pestanias = resultado
        
        # Agrupar por módulo
        modulos_dict = {pestania.modulo.id: pestania.modulo for pestania in pestanias}
        return list(modulos_dict.values())



    def pestanias_accesibles(self, modulo_uuid):
        from sistema.models import Pestania

        if self.is_superuser:
            pestanias = Pestania.objects.filter(status=1).filter(modulo__uuid=modulo_uuid).select_related("modulo").order_by("modulo__orden", "orden")
        else:
            mis_permisos = self.get_all_permissions()
            pestanias = Pestania.objects.filter(status=1).filter(modulo__uuid=modulo_uuid).select_related("modulo").prefetch_related("permission__content_type").order_by("modulo__orden", "orden")
            resultado = []
            for p in pestanias:
                perms_req = {f"{pm.content_type.app_label}.{pm.codename}" for pm in p.permission.all()}
                if not perms_req or (perms_req & mis_permisos):
                    resultado.append(p)
            pestanias = resultado
        return pestanias
        
    def __str__(self):
        return self.email
    
    
    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        today = now().date()
        return today.year - self.fecha_nacimiento.year - (
            (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )

    @property
    def departamento(self):
        return self.puesto.departamento if self.puesto else None


# class MaestroPerfil(BaseAcademico):
#     """Solo profesionales"""
#     tiene_certificado = models.BooleanField(default=False)
#     # Relative path
#     certificado = models.CharField(max_length=100, null=True, blank=True)
#     numero_cedula = models.CharField(max_length=100, null=True, blank=True)

#     class Meta:
#         db_table = "maestro_perfil"

# class EstudiantePerfil(BaseAcademico):
#     especialidad = models.CharField(max_length=50, null=True, blank=True)
#     matricula = models.CharField(max_length=50, null=True, blank=True, unique=True)
#     fecha_ingreso = models.DateField(null=True, blank=True)
#     ref = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

#     class Meta:
#         db_table = "estudiante_perfil"

class Role(Base):
    nombre = models.CharField(max_length=100, unique=True)
    permission = models.ManyToManyField(Permission)
    nivel_acceso = models.IntegerField(null=True, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        default_permissions = ()
        permissions = [
            ('ver_rol', 'Ver rol'),
            ('agregar_rol', 'Agregar rol'),
            ('editar_rol', 'Editar rol'),
            ('eliminar_rol', 'Eliminar rol'),
        ]
    
# class EstudianteUser(UserCustomize):
#     matricula = models.CharField(max_length=100, null=True, blank=True, unique=True)
#     fecha_ingreso = models.DateField(null=True, blank=True)
#     academic_profile = models.OneToOneField(AcademicProfile, on_delete=models.CASCADE, related_name="estudiante")
    
#     objects = CustomUserManager()

# class MaestroUser(UserCustomize):
#     numero_docente = models.CharField(max_length=100, null=True, blank=True)
#     fecha_ingreso = models.DateField(null=True, blank=True)
#     academic_profile = models.OneToOneField(AcademicProfile, on_delete=models.CASCADE, related_name="maestro")
#     especialidad = models.CharField(max_length=100, null=True, blank=True)
#     objects = CustomUserManager()

# class AdminUser(UserCustomize):
#     nivel_acceso = models.IntegerField(null=True, blank=True)



# Algo fundamental de @propierty vs @staticmethod es que la primera es un metodo que actua como atributo y el segunda es un metodo que actua como una funcion
# 
# @propierty computar valores getters y setters acceso a self sin cls metodo como atributo
# @staticmethod utilidades, helpers, fabricase sin acceso a self y cls impplicito metodo de clase
# 
# @classmethod recibe cls y puede acceder a atributos de la clase y metodos de la clase
# 