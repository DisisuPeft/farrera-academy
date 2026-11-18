from django.db import models
from django.conf import settings
from common.models import BaseModel


class Inscripcion(BaseModel):
    colaborador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='capacitacion_inscripcion_set',
    )
    curso = models.ForeignKey(
        'capacitacion.Curso',
        on_delete=models.PROTECT,
        related_name='inscripciones',
    )
    # Columna real, coexiste con `periodo` (decisión de plan 2026-11-10: ver
    # 02-DOCS/wiki/sdd/decisions.md). La invariante curso == periodo.curso NO
    # está garantizada todavía a este nivel del build — la impone InscripcionService
    # (T004), que es el único punto de escritura previsto para este campo. Hasta que
    # T004 exista, nada impide crear una Inscripcion con curso/periodo divergentes.
    periodo = models.ForeignKey(
        'capacitacion.Periodo',
        on_delete=models.PROTECT,
        related_name='inscripciones',
    )
    inscrito_at = models.DateTimeField(auto_now_add=True)
    completado_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-inscrito_at']
        verbose_name = 'Inscripción'
        verbose_name_plural = 'Inscripciones'
        unique_together = [('colaborador', 'periodo')]
        default_permissions = ()
        permissions = [
            ('ver_inscripcion', 'Ver inscripción'),
            ('agregar_inscripcion', 'Agregar inscripción'),
        ]

    def __str__(self):
        return f'{self.colaborador} → {self.curso}'


class ProgresoTema(BaseModel):
    inscripcion = models.ForeignKey(
        'capacitacion.Inscripcion',
        on_delete=models.PROTECT,
        related_name='progresos_tema',
    )
    tema = models.ForeignKey(
        'capacitacion.Tema',
        on_delete=models.PROTECT,
        related_name='progresos',
    )
    completado_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completado_at']
        verbose_name = 'Progreso de tema'
        verbose_name_plural = 'Progresos de tema'
        unique_together = [('inscripcion', 'tema')]
        default_permissions = ()

    def __str__(self):
        return f'{self.inscripcion.colaborador} → {self.tema}'


class ResultadoEvaluacion(BaseModel):
    inscripcion = models.ForeignKey(
        'capacitacion.Inscripcion',
        on_delete=models.PROTECT,
        related_name='resultados_evaluacion',
    )
    evaluacion = models.ForeignKey(
        'capacitacion.Evaluacion',
        on_delete=models.PROTECT,
        related_name='resultados',
    )
    correctas = models.PositiveSmallIntegerField(default=0)
    total = models.PositiveSmallIntegerField(default=0)
    presentado_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-presentado_at']
        verbose_name = 'Resultado de evaluación'
        verbose_name_plural = 'Resultados de evaluación'
        default_permissions = ()

    def __str__(self):
        return f'{self.inscripcion.colaborador} → {self.evaluacion} ({self.correctas}/{self.total})'
