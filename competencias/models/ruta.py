from django.db import models
from common.models import BaseModel, SoftDeleteModel


class RutaAprendizaje(BaseModel, SoftDeleteModel):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    competencia = models.ForeignKey(
        'competencias.Competencia',
        on_delete=models.PROTECT,
        related_name='rutas',
    )
    nivel_objetivo = models.ForeignKey(
        'catalogos.NivelCompetencia',
        on_delete=models.PROTECT,
        related_name='rutas',
    )
    cursos = models.ManyToManyField(
        'capacitacion.Curso',
        through='RutaAprendizajeCurso',
        related_name='rutas',
    )

    class Meta:
        ordering = ['competencia', 'nombre']
        verbose_name = 'Ruta de aprendizaje'
        verbose_name_plural = 'Rutas de aprendizaje'
        default_permissions = ()
        permissions = [
            ('ver_ruta_aprendizaje', 'Ver ruta de aprendizaje'),
            ('agregar_ruta_aprendizaje', 'Agregar ruta de aprendizaje'),
            ('editar_ruta_aprendizaje', 'Editar ruta de aprendizaje'),
            ('eliminar_ruta_aprendizaje', 'Eliminar ruta de aprendizaje'),
        ]

    def __str__(self):
        return f'{self.nombre} → {self.nivel_objetivo}'


class RutaAprendizajeCurso(BaseModel):
    ruta = models.ForeignKey(
        RutaAprendizaje,
        on_delete=models.CASCADE,
        related_name='ruta_cursos',
    )
    curso = models.ForeignKey(
        'capacitacion.Curso',
        on_delete=models.PROTECT,
        related_name='ruta_cursos',
    )
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ruta', 'orden']
        verbose_name = 'Curso en ruta de aprendizaje'
        verbose_name_plural = 'Cursos en ruta de aprendizaje'
        unique_together = [('ruta', 'orden'), ('ruta', 'curso')]
        default_permissions = ()

    def __str__(self):
        return f'{self.ruta} — paso {self.orden}: {self.curso}'