from django.conf import settings
from django.db import models
from common.models import BaseModel, BaseFileEntity


class Curso(BaseModel):
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    duracion_horas = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    imagen = models.ImageField(upload_to='capacitacion/cursos/imagenes/', blank=True)
    banner = models.ImageField(upload_to='capacitacion/cursos/banners/', blank=True)
    status = models.ForeignKey(
        'catalogos.CatalogStatus',
        on_delete=models.PROTECT,
        related_name='cursos',
    )
    # Ámbito de autorización: nulo = curso "global" (compatibilidad con datos existentes,
    # visible para cualquier Administrador). Con empresa asignada, solo lo administran
    # los usuarios cuya `dependencia.empresa` coincide (ver CursoViewSet.get_queryset).
    empresa = models.ForeignKey(
        'sistema.Empresa',
        on_delete=models.PROTECT,
        related_name='cursos',
        null=True,
        blank=True,
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='cursos_creados',
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['titulo']
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        default_permissions = ()
        permissions = [
            ('ver_curso', 'Ver curso'),
            ('agregar_curso', 'Agregar curso'),
            ('editar_curso', 'Editar curso'),
            ('eliminar_curso', 'Eliminar curso'),
        ]

    def __str__(self):
        return self.titulo


class Periodo(BaseModel):
    class Estado(models.TextChoices):
        ABIERTO = 'abierto', 'Abierto'
        CERRADO = 'cerrado', 'Cerrado'

    curso = models.ForeignKey(
        'capacitacion.Curso',
        on_delete=models.PROTECT,
        related_name='periodos',
    )
    nombre = models.CharField(max_length=255)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ABIERTO)

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = 'Periodo de impartición'
        verbose_name_plural = 'Periodos de impartición'
        default_permissions = ()
        permissions = [
            ('ver_periodo', 'Ver periodo'),
            ('agregar_periodo', 'Agregar periodo'),
            ('editar_periodo', 'Editar periodo'),
            ('eliminar_periodo', 'Eliminar periodo'),
        ]

    def __str__(self):
        return f'{self.curso} — {self.nombre}'


class Modulo(BaseModel):
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name='modulos',
    )
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveSmallIntegerField(default=0)
    horas_teoricas = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    horas_practicas = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tiene_evaluacion = models.BooleanField(default=False)

    class Meta:
        ordering = ['curso', 'orden']
        verbose_name = 'Módulo'
        verbose_name_plural = 'Módulos'
        unique_together = [('curso', 'orden')]
        default_permissions = ()

    def __str__(self):
        return f'{self.curso} — {self.titulo}'


class Tema(BaseModel):
    modulo = models.ForeignKey(
        Modulo,
        on_delete=models.CASCADE,
        related_name='temas',
    )
    titulo = models.CharField(max_length=255)
    duracion_estimada = models.CharField(max_length=20, blank=True)
    tipo = models.ForeignKey(
        'catalogos.TipeTema',
        on_delete=models.PROTECT,
        related_name='temas',
    )
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['modulo', 'orden']
        verbose_name = 'Tema'
        verbose_name_plural = 'Temas'
        unique_together = [('modulo', 'orden')]
        default_permissions = ()

    def __str__(self):
        return f'{self.modulo} — {self.titulo}'


class ContenidoBloque(BaseModel):
    tema = models.ForeignKey(
        Tema,
        on_delete=models.CASCADE,
        related_name='bloques',
    )
    tipo = models.ForeignKey(
        'catalogos.TipoBloqueContenido',
        on_delete=models.PROTECT,
        related_name='bloques',
    )
    orden = models.PositiveSmallIntegerField(default=0)
    texto = models.TextField(blank=True)
    variante = models.CharField(max_length=20, blank=True)
    items = models.JSONField(null=True, blank=True)
    filas = models.JSONField(null=True, blank=True)
    video_url = models.CharField(max_length=500, blank=True)
    video_archivo = models.FileField(
        upload_to='capacitacion/videos/',
        blank=True,
        null=True,
    )
    imagen_url = models.CharField(max_length=500, blank=True)
    imagen_archivo = models.ImageField(
        upload_to='capacitacion/imagenes/bloques/',
        blank=True,
        null=True,
    )
    embed_url = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['tema', 'orden']
        verbose_name = 'Bloque de contenido'
        verbose_name_plural = 'Bloques de contenido'
        unique_together = [('tema', 'orden')]
        default_permissions = ()

    def __str__(self):
        return f'{self.tema} — bloque {self.orden} ({self.tipo})'


class ContenidoBloqueItem(BaseModel):
    """
    Ítem individual dentro de un bloque de tipo 'texto-tarjetas', 'texto-paneles',
    'texto-presentacion' o 'texto-presentacion-paneles' (una tarjeta, un panel o
    una diapositiva). Es un registro propio — y no un elemento más de un JSONField —
    porque cada uno necesita poder llevar su propia imagen subida.
    """
    bloque = models.ForeignKey(
        ContenidoBloque,
        on_delete=models.CASCADE,
        related_name='bloque_items',
    )
    orden = models.PositiveSmallIntegerField(default=0)
    titulo = models.CharField(max_length=255, blank=True)
    texto = models.TextField(blank=True)
    imagen_url = models.CharField(max_length=500, blank=True)
    imagen_archivo = models.ImageField(
        upload_to='capacitacion/imagenes/items/',
        blank=True,
        null=True,
    )
    # Datos libres propios del ítem (ej. la lista de ubicaciones de un panel de agencias)
    items = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['bloque', 'orden']
        verbose_name = 'Ítem de bloque'
        verbose_name_plural = 'Ítems de bloque'
        unique_together = [('bloque', 'orden')]
        default_permissions = ()

    def __str__(self):
        return f'{self.bloque} — item {self.orden}'


class ContenidoBloqueArchivo(BaseFileEntity):
    """
    Adjunto genérico de un bloque (audio, documento descargable, etc.).
    Reutiliza BaseFileEntity (common/models.py) en vez de inventar un campo de
    archivo distinto por tipo: ya trae mime_type, file_type, tamaño, checksum
    y detección automática. Un bloque puede tener varios (ej. documento +
    sus anexos), ordenados con el mismo patrón `orden` que el resto del árbol.
    """
    bloque = models.ForeignKey(
        ContenidoBloque,
        on_delete=models.CASCADE,
        related_name='archivos',
    )
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['bloque', 'orden']
        verbose_name = 'Archivo de bloque'
        verbose_name_plural = 'Archivos de bloque'
        unique_together = [('bloque', 'orden')]
        default_permissions = ()


class ContenidoBloqueOpcion(BaseModel):
    """
    Opción de respuesta para bloques evaluativos ligeros embebidos directamente
    en una lección (tipo 'opcion-multiple' o 'verdadero-falso' dentro de un
    Tema), DISTINTOS del sistema formal de Evaluacion/Pregunta/OpcionPregunta
    (evaluación de módulo/curso con puntaje mínimo). `es_correcta` es dato de
    autoría y nunca se expone a un colaborador (ver serializers de colaborador).
    """
    bloque = models.ForeignKey(
        ContenidoBloque,
        on_delete=models.CASCADE,
        related_name='opciones',
    )
    orden = models.PositiveSmallIntegerField(default=0)
    texto = models.CharField(max_length=255)
    es_correcta = models.BooleanField(default=False)

    class Meta:
        ordering = ['bloque', 'orden']
        verbose_name = 'Opción de bloque evaluativo'
        verbose_name_plural = 'Opciones de bloque evaluativo'
        unique_together = [('bloque', 'orden')]
        default_permissions = ()

    def __str__(self):
        return f'{self.bloque} — opción {self.orden}'


class ContenidoBloqueRespuesta(BaseModel):
    """
    Intento de un colaborador sobre un bloque evaluativo embebido. `es_correcta`
    se calcula en el servidor al crear el registro (nunca se recibe del
    cliente), igual que en ResultadoEvaluacion — mismo patrón, menor peso.
    """
    inscripcion = models.ForeignKey(
        'capacitacion.Inscripcion',
        on_delete=models.PROTECT,
        related_name='respuestas_bloque',
    )
    bloque = models.ForeignKey(
        ContenidoBloque,
        on_delete=models.PROTECT,
        related_name='respuestas',
    )
    opcion_seleccionada = models.ForeignKey(
        ContenidoBloqueOpcion,
        on_delete=models.PROTECT,
        related_name='respuestas',
    )
    es_correcta = models.BooleanField()
    respondido_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-respondido_at']
        verbose_name = 'Respuesta de bloque evaluativo'
        verbose_name_plural = 'Respuestas de bloque evaluativo'
        default_permissions = ()

    def __str__(self):
        return f'{self.inscripcion.colaborador} → {self.bloque} ({"correcta" if self.es_correcta else "incorrecta"})'
