from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from capacitacion.models import Evaluacion, Inscripcion, ProgresoTema, ResultadoEvaluacion, Tema


class YaFinalizada:
    pass


class FinalizacionService:
    @staticmethod
    def _finalizar(inscripcion):
        from competencias.services.acreditacion_service import AcreditacionService

        inscripcion.completado_at = timezone.now()
        inscripcion.save(update_fields=['completado_at'])
        AcreditacionService.acreditar(inscripcion)

    @staticmethod
    def _criterio_cumplido(inscripcion):
        temas_curso = Tema.objects.filter(modulo__curso=inscripcion.curso, activo=True)
        if not temas_curso.exists():
            return False

        temas_con_progreso = ProgresoTema.objects.filter(
            inscripcion=inscripcion, tema__in=temas_curso,
        ).values_list('tema_id', flat=True)
        if set(temas_con_progreso) != set(temas_curso.values_list('id', flat=True)):
            return False

        evaluaciones_curso = Evaluacion.objects.filter(
            Q(curso=inscripcion.curso) | Q(modulo__curso=inscripcion.curso),
        )
        for evaluacion in evaluaciones_curso:
            resultados = ResultadoEvaluacion.objects.filter(inscripcion=inscripcion, evaluacion=evaluacion)
            aprobada = any(
                r.total > 0 and (r.correctas / r.total) * 100 >= evaluacion.puntaje_minimo
                for r in resultados
            )
            if not aprobada:
                return False

        return True

    @staticmethod
    def reevaluar(inscripcion):
        with transaction.atomic():
            inscripcion = Inscripcion.objects.select_for_update().get(pk=inscripcion.pk)

            if inscripcion.completado_at is not None:
                return inscripcion

            if FinalizacionService._criterio_cumplido(inscripcion):
                FinalizacionService._finalizar(inscripcion)

            return inscripcion

    @staticmethod
    def forzar(inscripcion, actor):
        """Finalización excepcional por un administrador — mismo efecto
        observable que `reevaluar()` al finalizar (mismo `completado_at`,
        misma acreditación), pero sin exigir el criterio normal. La
        autorización (`actor` con rol Administrador) la exige el permiso
        `HasRoleWithRoles(['Administrador'])` en el endpoint; este método
        confía en que ya se validó antes de llegar aquí."""
        with transaction.atomic():
            inscripcion = Inscripcion.objects.select_for_update().get(pk=inscripcion.pk)

            if inscripcion.completado_at is not None:
                return YaFinalizada()

            FinalizacionService._finalizar(inscripcion)

            return inscripcion
