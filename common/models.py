from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.utils.date import get_today
from core.utils.date import get_formatted_short_date
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
import os
import mimetypes
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils.text import get_valid_filename
import uuid
from core.utils.file_helpers import generic_upload_path
# Create your models here.

class BaseModel(models.Model):
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        abstract = True


# modelo base para registros
class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(app_label)s_%(class)s_deleted_by')

    def delete(self, using=None, keep_parents=False, user=None):
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['deleted_at', 'deleted_by'])
    
    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['deleted_at', 'deleted_by'])

    class Meta:
        abstract = True

class OwnerBaseModel(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='%(app_label)s_%(class)s_owner', null=True, blank=True)
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(app_label)s_%(class)s_edited_by')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(app_label)s_%(class)s_created_by')
    class Meta:
        abstract = True

# Modelo base para los usuario o modelos que no requieran soft delete
class Base(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(default=1)

    class Meta:
        abstract = True
    
    @property
    def created_at_format(self):
        return self.created_at.strftime('%Y-%m-%d %H:%M:%S')
    
    @property
    def is_recent(self):
        return (timezone.now() - self.created_at).days < 7


class BaseFileEntity(Base):
    """
    Modelo base abstracto para gestión de archivos con metadata rica.
    """

    class FileType(models.TextChoices):
        DOCUMENT = 'document', 'Documento'
        IMAGE = 'image', 'Imagen'
        VIDEO = 'video', 'Video'
        AUDIO = 'audio', 'Audio'
        SPREADSHEET = 'spreadsheet', 'Hoja de cálculo'
        PRESENTATION = 'presentation', 'Presentación'
        ARCHIVE = 'archive', 'Archivo comprimido'
        OTHER = 'other', 'Otro'

    # ========== ARCHIVO FÍSICO ==========
    file = models.FileField(
        upload_to=generic_upload_path,  # ← Función genérica por defecto
        max_length=500,
        verbose_name="Archivo",
        help_text="Archivo físico almacenado",
        # null=True,
        # blank=True
    )

    # ========== METADATA BÁSICA ==========
    original_name = models.CharField(
        max_length=500,
        verbose_name="Nombre original",
        help_text="Nombre original del archivo al momento de subirlo",
        null = True,
        blank = True
    )

    mime_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Tipo MIME",
        help_text="Tipo MIME detectado automáticamente"
    )

    size = models.BigIntegerField(
        default=0,
        verbose_name="Tamaño (bytes)",
        help_text="Tamaño del archivo en bytes"
    )

    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices,
        default=FileType.OTHER,
        db_index=True,
        verbose_name="Tipo de archivo",
        help_text="Categoría del archivo detectada automáticamente"
    )

    # ========== METADATA EXTENDIDA ==========
    description = models.TextField(
        blank=True,
        verbose_name="Descripción",
        help_text="Descripción opcional del archivo"
    )

    # ========== PERMISOS Y VISIBILIDAD ==========
    is_public = models.BooleanField(
        default=False,
        verbose_name="¿Es público?",
        help_text="¿Puede ser accedido sin autenticación?"
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_uploaded',
        verbose_name="Subido por"
    )

    # ========== CHECKSUM ==========
    checksum = models.CharField(
        max_length=64,
        blank=True,
        editable=False,
        verbose_name="Checksum (SHA256)",
        help_text="Hash del archivo para verificar integridad"
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mime_type', 'created_at']),
            models.Index(fields=['file_type', 'status']),
            models.Index(fields=['uploaded_by', 'created_at']),
        ]

    def __str__(self):
        return f"{self.original_name} ({self.get_file_type_display()})"

    # ========== MÉTODOS DE GUARDADO ==========
    def save(self, *args, **kwargs):
        """Override para auto-llenar metadata desde el archivo."""
        if self.file:
            # Auto-llenar nombre original
            if not self.original_name:
                self.original_name = os.path.basename(self.file.name)

            # Auto-detectar MIME type
            if not self.mime_type:
                self.mime_type = self._detect_mime_type()

            # Auto-llenar tamaño
            if not self.size and hasattr(self.file, 'size'):
                self.size = self.file.size

            # Auto-detectar tipo de archivo
            if self.file_type == self.FileType.OTHER:
                self.file_type = self._detect_file_type()

            # Generar checksum solo en creación
            if not self.pk and not self.checksum:
                self.checksum = self._generate_checksum()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Override para eliminar archivo físico al eliminar registro."""
        if self.file:
            try:
                if os.path.isfile(self.file.path):
                    os.remove(self.file.path)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error al eliminar archivo {self.file.path}: {e}")

        super().delete(*args, **kwargs)

    # ========== MÉTODOS PRIVADOS ==========
    def _detect_mime_type(self):
        """Detectar tipo MIME del archivo."""
        mime_type, _ = mimetypes.guess_type(self.file.name)
        return mime_type or 'application/octet-stream'

    def _detect_file_type(self):
        """Detectar categoría del archivo basado en MIME type."""
        mime = self.mime_type.lower()

        if mime.startswith('image/'):
            return self.FileType.IMAGE
        elif mime.startswith('video/'):
            return self.FileType.VIDEO
        elif mime.startswith('audio/'):
            return self.FileType.AUDIO
        elif mime in ['application/pdf', 'application/msword',
                      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                      'text/plain', 'application/rtf']:
            return self.FileType.DOCUMENT
        elif mime in ['application/vnd.ms-excel',
                      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                      'text/csv']:
            return self.FileType.SPREADSHEET
        elif mime in ['application/vnd.ms-powerpoint',
                      'application/vnd.openxmlformats-officedocument.presentationml.presentation']:
            return self.FileType.PRESENTATION
        elif mime in ['application/zip', 'application/x-rar-compressed',
                      'application/x-7z-compressed', 'application/gzip']:
            return self.FileType.ARCHIVE
        else:
            return self.FileType.OTHER

    def _generate_checksum(self):
        """Generar hash SHA256 del archivo."""
        import hashlib

        if not self.file:
            return ''

        try:
            sha256 = hashlib.sha256()
            # Leer en chunks para archivos grandes
            for chunk in self.file.chunks():
                sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return ''

    # ========== PROPERTIES ==========
    @property
    def file_extension(self):
        """Obtener extensión del archivo."""
        if '.' in self.original_name:
            return self.original_name.split('.')[-1].lower()
        return ''

    @property
    def size_formatted(self):
        """Tamaño formateado (KB, MB, GB)."""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 ** 2:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024 ** 3:
            return f"{self.size / (1024 ** 2):.1f} MB"
        else:
            return f"{self.size / (1024 ** 3):.1f} GB"

    @property
    def download_url(self):
        """URL para descargar el archivo."""
        if self.file:
            return self.file.url
        return None

    @property
    def is_image(self):
        """Verificar si es una imagen."""
        return self.file_type == self.FileType.IMAGE

    @property
    def is_document(self):
        """Verificar si es un documento."""
        return self.file_type == self.FileType.DOCUMENT

    @property
    def can_preview(self):
        """Verificar si el archivo puede previsualizarse."""
        if self.file_type == self.FileType.IMAGE:
            return True
        if self.file_type == self.FileType.DOCUMENT:
            return self.mime_type == 'application/pdf'
        return False



class BaseAcademico(Base):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='%(app_label)s_%(class)s_user', null=True, blank=True)
    nivel_educativo = models.ForeignKey('catalogos.NivelEducativo', on_delete=models.CASCADE, related_name='%(app_label)s_%(class)s_nivel', null=True, blank=True)
    institucion = models.ForeignKey('catalogos.Institucion', on_delete=models.CASCADE, related_name='%(app_label)s_%(class)s_institucion', null=True, blank=True)
    estado_pais = models.ForeignKey("catalogos.EstadoPais", on_delete=models.CASCADE, related_name="%(app_label)s_%(class)s_estado_pais", null=True, blank=True)
    ciudad = models.ForeignKey("catalogos.Localidad", on_delete=models.CASCADE, related_name="%(app_label)s_%(class)s_ciudad", null=True, blank=True)

    class Meta:
        abstract = True
        
class BaseCRM(Base, SoftDeleteModel):
    empresa = models.ForeignKey('sistema.Empresa', on_delete=models.CASCADE, related_name='%(app_label)s_%(class)s_empresa', null=True, blank=True)
    instituto = models.ForeignKey('catalogos.Institucion', on_delete=models.CASCADE, related_name='%(app_label)s_%(class)s_instituto', null=True, blank=True)

    class Meta:
        abstract = True