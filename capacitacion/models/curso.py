from django.db import models
from common.models import BaseModel


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

    class Meta:
        ordering = ['tema', 'orden']
        verbose_name = 'Bloque de contenido'
        verbose_name_plural = 'Bloques de contenido'
        unique_together = [('tema', 'orden')]
        default_permissions = ()

    def __str__(self):
        return f'{self.tema} — bloque {self.orden} ({self.tipo})'
