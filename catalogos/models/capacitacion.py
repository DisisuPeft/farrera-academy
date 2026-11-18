from django.db import models
from .base import BaseCatalogo


class CategoriaPedagogica(models.TextChoices):
    CONTENIDO = 'contenido', 'Contenido'
    EXPLORACION = 'exploracion', 'Exploración'
    PRACTICA = 'practica', 'Práctica'
    EVALUACION = 'evaluacion', 'Evaluación'
    REFLEXION_COLABORACION = 'reflexion_colaboracion', 'Reflexión y colaboración'
    ESTRUCTURA_NAVEGACION = 'estructura_navegacion', 'Estructura y navegación'


class CatalogStatus(BaseCatalogo):
    class Meta(BaseCatalogo.Meta):
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'
        permissions = [
            ('ver_catalogstatus', 'Ver estado de catálogo'),
            ('agregar_catalogstatus', 'Agregar estado de catálogo'),
            ('editar_catalogstatus', 'Editar estado de catálogo'),
            ('eliminar_catalogstatus', 'Eliminar estado de catálogo'),
        ]


class TipoBloqueContenido(BaseCatalogo):
    """
    Catálogo extensible de tipos de bloque educativo (contenido, exploración,
    práctica, evaluación, reflexión/colaboración, estructura/navegación).

    `config` define los campos propios del tipo y sus valores por defecto para
    que el frontend pueda construir el formulario de autoría sin casos
    especiales por tipo (ej. {"campos": ["texto", "imagen_url"], "defaults": {...}}).
    `validacion_schema` es un JSON Schema (borrador 2020-12) opcional contra el
    que se valida `ContenidoBloque.items`/`filas`/config de cada instancia.
    `capacidades` es una lista simple de banderas que el frontend puede
    consultar sin parsear el schema (ej. ["soporta_imagen", "requiere_items"]).
    `version_esquema` sube cuando cambia la forma esperada del contenido, para
    que instancias antiguas puedan seguir interpretándose con su propia versión.
    """

    categoria = models.CharField(
        max_length=30,
        choices=CategoriaPedagogica.choices,
        default=CategoriaPedagogica.CONTENIDO,
    )
    descripcion = models.CharField(max_length=255, blank=True)
    config = models.JSONField(null=True, blank=True)
    validacion_schema = models.JSONField(null=True, blank=True)
    capacidades = models.JSONField(null=True, blank=True)
    version_esquema = models.PositiveSmallIntegerField(default=1)

    class Meta(BaseCatalogo.Meta):
        verbose_name = 'Tipo de bloque de contenido'
        verbose_name_plural = 'Tipos de bloque de contenido'
        permissions = [
            ('ver_tipobloquecontenido', 'Ver tipo de bloque de contenido'),
            ('agregar_tipobloquecontenido', 'Agregar tipo de bloque de contenido'),
            ('editar_tipobloquecontenido', 'Editar tipo de bloque de contenido'),
            ('eliminar_tipobloquecontenido', 'Eliminar tipo de bloque de contenido'),
        ]


class TipeTema(BaseCatalogo):
    """Tipos de tema: lectura, video, actividad, etc."""

    class Meta(BaseCatalogo.Meta):
        verbose_name = 'Tipo de tema'
        verbose_name_plural = 'Tipos de tema'
        permissions = [
            ('ver_tipetema', 'Ver tipo de tema'),
            ('agregar_tipetema', 'Agregar tipo de tema'),
            ('editar_tipetema', 'Editar tipo de tema'),
            ('eliminar_tipetema', 'Eliminar tipo de tema'),
        ]


class TipoEvaluacion(BaseCatalogo):
    """Tipos de evaluación: modulo, final, etc."""

    class Meta(BaseCatalogo.Meta):
        verbose_name = 'Tipo de evaluación'
        verbose_name_plural = 'Tipos de evaluación'
        permissions = [
            ('ver_tipoevaluacion', 'Ver tipo de evaluación'),
            ('agregar_tipoevaluacion', 'Agregar tipo de evaluación'),
            ('editar_tipoevaluacion', 'Editar tipo de evaluación'),
            ('eliminar_tipoevaluacion', 'Eliminar tipo de evaluación'),
        ]
