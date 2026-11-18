class AcreditacionService:
    """Única puerta de entrada para otorgar nivel de competencia por haber
    completado un curso. Llamada solo desde FinalizacionService, en la misma
    transacción que finaliza la inscripción — nunca desde un signal, para
    que una inscripción histórica ya acreditada no se reevalúe al volver a
    guardarse (ver decisions.md, hallazgo de la auditoría / AC7)."""

    @staticmethod
    def acreditar(inscripcion):
        from competencias.models import CompetenciaColaborador
        from competencias.models.competencia import CompetenciaCurso

        competencia_cursos = CompetenciaCurso.objects.filter(
            curso=inscripcion.curso,
            activo=True,
        ).select_related('competencia', 'nivel')

        for cc in competencia_cursos:
            registro = CompetenciaColaborador.objects.filter(
                colaborador=inscripcion.colaborador,
                competencia=cc.competencia,
            ).select_related('nivel').first()

            if registro is None:
                CompetenciaColaborador.objects.create(
                    colaborador=inscripcion.colaborador,
                    competencia=cc.competencia,
                    nivel=cc.nivel,
                    origen=inscripcion,
                )
            elif cc.nivel.orden > registro.nivel.orden:
                registro.nivel = cc.nivel
                registro.origen = inscripcion
                registro.save(update_fields=['nivel', 'origen', 'actualizado_at'])
