from .base import BaseCatalogo


class CatalogStatus(BaseCatalogo):
    class Meta(BaseCatalogo.Meta):
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'


class TipoBloqueContenido(BaseCatalogo):
    """Tipos de bloque: parrafo, subtitulo, lista, tabla, alerta, video, etc."""

    class Meta(BaseCatalogo.Meta):
        verbose_name = 'Tipo de bloque de contenido'
        verbose_name_plural = 'Tipos de bloque de contenido'


class TipeTema(BaseCatalogo):
    """Tipos de tema: lectura, video, actividad, etc."""

    class Meta(BaseCatalogo.Meta):
        verbose_name = 'Tipo de tema'
        verbose_name_plural = 'Tipos de tema'


class TipoEvaluacion(BaseCatalogo):
    """Tipos de evaluación: modulo, final, etc."""

    class Meta(BaseCatalogo.Meta):
        verbose_name = 'Tipo de evaluación'
        verbose_name_plural = 'Tipos de evaluación'
