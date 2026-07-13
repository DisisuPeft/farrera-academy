from django.db import models
from django.conf import settings
from common.models import BaseModel


class CompetenciaColaborador(BaseModel):
    colaborador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='competencias_colaborador',
    )
    competencia = models.ForeignKey(
        'competencias.Competencia',
        on_delete=models.PROTECT,
        related_name='competencia_colaboradores',
    )
    nivel = models.ForeignKey(
        'catalogos.NivelCompetencia',
        on_delete=models.PROTECT,
        related_name='competencia_colaboradores',
    )
    # inscripcion que generó o actualizó este nivel (null = asignado manualmente)
    origen = models.ForeignKey(
        'capacitacion.Inscripcion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='competencias_ganadas',
    )

    class Meta:
        ordering = ['colaborador', 'competencia']
        verbose_name = 'Competencia de colaborador'
        verbose_name_plural = 'Competencias de colaboradores'
        unique_together = [('colaborador', 'competencia')]
        default_permissions = ()
        permissions = [
            ('ver_competencia_colaborador', 'Ver competencia de colaborador'),
            ('editar_competencia_colaborador', 'Editar competencia de colaborador'),
        ]

    def __str__(self):
        return f'{self.colaborador} → {self.competencia} [{self.nivel}]'