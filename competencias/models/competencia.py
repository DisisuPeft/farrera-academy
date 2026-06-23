from django.db import models
from common.models import BaseModel, SoftDeleteModel


class Competencia(BaseModel, SoftDeleteModel):
    nombre = models.CharField(max_length=120)
    codigo = models.SlugField(unique=True)
    descripcion = models.TextField(blank=True)
    icono = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Competencia'
        verbose_name_plural = 'Competencias'
        default_permissions = ()
        permissions = [
            ('ver_competencia', 'Ver competencia'),
            ('agregar_competencia', 'Agregar competencia'),
            ('editar_competencia', 'Editar competencia'),
            ('eliminar_competencia', 'Eliminar competencia'),
        ]

    def __str__(self):
        return self.nombre


class CompetenciaCurso(BaseModel, SoftDeleteModel):
    competencia = models.ForeignKey(
        Competencia,
        on_delete=models.PROTECT,
        related_name='competencia_cursos',
    )
    curso = models.ForeignKey(
        'capacitacion.Curso',
        on_delete=models.PROTECT,
        related_name='competencia_cursos',
    )
    nivel = models.ForeignKey(
        'catalogos.NivelCompetencia',
        on_delete=models.PROTECT,
        related_name='competencia_cursos',
    )

    class Meta:
        ordering = ['competencia', 'curso']
        verbose_name = 'Competencia por curso'
        verbose_name_plural = 'Competencias por curso'
        unique_together = [('competencia', 'curso')]
        default_permissions = ()
        permissions = [
            ('ver_competencia_curso', 'Ver competencia por curso'),
            ('agregar_competencia_curso', 'Agregar competencia por curso'),
            ('editar_competencia_curso', 'Editar competencia por curso'),
            ('eliminar_competencia_curso', 'Eliminar competencia por curso'),
        ]

    def __str__(self):
        return f'{self.competencia} → {self.curso} [{self.nivel}]'


class CompetenciaPuesto(BaseModel, SoftDeleteModel):
    competencia = models.ForeignKey(
        Competencia,
        on_delete=models.PROTECT,
        related_name='competencia_puestos',
    )
    puesto = models.ForeignKey(
        'sistema.Puesto',
        on_delete=models.PROTECT,
        related_name='competencia_puestos',
    )
    nivel = models.ForeignKey(
        'catalogos.NivelCompetencia',
        on_delete=models.PROTECT,
        related_name='puesto_competencias',
    )

    class Meta:
        ordering = ['competencia', 'puesto']
        verbose_name = 'Competencia por puesto'
        verbose_name_plural = 'Competencias por puesto'
        unique_together = [('competencia', 'puesto')]
        default_permissions = ()
        permissions = [
            ('ver_competencia_puesto', 'Ver competencia por puesto'),
            ('agregar_competencia_puesto', 'Agregar competencia por puesto'),
            ('editar_competencia_puesto', 'Editar competencia por puesto'),
            ('eliminar_competencia_puesto', 'Eliminar competencia por puesto'),
        ]

    def __str__(self):
        return f'{self.competencia} → {self.puesto} [{self.nivel}]'
