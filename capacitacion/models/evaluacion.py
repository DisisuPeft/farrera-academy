from django.core.exceptions import ValidationError
from django.db import models
from common.models import BaseModel


class Evaluacion(BaseModel):
    titulo = models.CharField(max_length=255)
    tipo = models.ForeignKey(
        'catalogos.TipoEvaluacion',
        on_delete=models.PROTECT,
        related_name='evaluaciones',
    )
    puntaje_minimo = models.DecimalField(max_digits=5, decimal_places=2, default=70)
    curso = models.ForeignKey(
        'capacitacion.Curso',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='evaluaciones',
    )
    modulo = models.ForeignKey(
        'capacitacion.Modulo',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='evaluaciones',
    )

    class Meta:
        ordering = ['titulo']
        verbose_name = 'Evaluación'
        verbose_name_plural = 'Evaluaciones'
        default_permissions = ()

    def clean(self):
        ambos = self.curso_id and self.modulo_id
        ninguno = not self.curso_id and not self.modulo_id
        if ambos:
            raise ValidationError('Una evaluación no puede pertenecer a un curso y a un módulo al mismo tiempo.')
        if ninguno:
            raise ValidationError('Una evaluación debe pertenecer a un curso o a un módulo.')

    def __str__(self):
        return self.titulo


class Pregunta(BaseModel):
    evaluacion = models.ForeignKey(
        Evaluacion,
        on_delete=models.CASCADE,
        related_name='preguntas',
    )
    texto = models.TextField()
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['evaluacion', 'orden']
        verbose_name = 'Pregunta'
        verbose_name_plural = 'Preguntas'
        unique_together = [('evaluacion', 'orden')]
        default_permissions = ()

    def __str__(self):
        return f'{self.evaluacion} — pregunta {self.orden}'


class OpcionPregunta(BaseModel):
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE,
        related_name='opciones',
    )
    texto = models.TextField()
    orden = models.PositiveSmallIntegerField(default=0)
    es_correcta = models.BooleanField(default=False)

    class Meta:
        ordering = ['pregunta', 'orden']
        verbose_name = 'Opción de pregunta'
        verbose_name_plural = 'Opciones de pregunta'
        unique_together = [('pregunta', 'orden')]
        default_permissions = ()

    def __str__(self):
        return f'{self.pregunta} — opción {self.orden}'
