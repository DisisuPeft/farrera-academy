from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='capacitacion.Inscripcion')
def acreditar_competencias_al_completar(sender, instance, **kwargs):
    """
    Cuando una Inscripcion se marca como completada, revisa qué competencias
    aporta ese curso (CompetenciaCurso) y sube el nivel del colaborador
    (CompetenciaColaborador) si el nivel ganado es mayor al actual.
    Solo sube, nunca retrocede.
    """
    if not instance.completado_at:
        return

    # Importaciones locales para evitar circular imports
    from competencias.models import CompetenciaColaborador
    from competencias.models.competencia import CompetenciaCurso

    competencia_cursos = CompetenciaCurso.objects.filter(
        curso=instance.curso,
        activo=True,
    ).select_related('competencia', 'nivel')

    for cc in competencia_cursos:
        registro = CompetenciaColaborador.objects.filter(
            colaborador=instance.colaborador,
            competencia=cc.competencia,
        ).select_related('nivel').first()

        if registro is None:
            CompetenciaColaborador.objects.create(
                colaborador=instance.colaborador,
                competencia=cc.competencia,
                nivel=cc.nivel,
                origen=instance,
            )
        elif cc.nivel.orden > registro.nivel.orden:
            registro.nivel = cc.nivel
            registro.origen = instance
            registro.save(update_fields=['nivel', 'origen', 'actualizado_at'])