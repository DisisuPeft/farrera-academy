from django.db import IntegrityError, transaction

from capacitacion.models import Inscripcion, Periodo


class PeriodoNoAbierto:
    pass


class InscripcionDuplicada:
    pass


class InscripcionService:
    @staticmethod
    def crear(colaborador, periodo):
        with transaction.atomic():
            periodo_bloqueado = Periodo.objects.select_for_update().get(pk=periodo.pk)
            if periodo_bloqueado.estado != Periodo.Estado.ABIERTO:
                return PeriodoNoAbierto()

            try:
                with transaction.atomic():
                    return Inscripcion.objects.create(
                        colaborador=colaborador,
                        curso=periodo_bloqueado.curso,
                        periodo=periodo_bloqueado,
                    )
            except IntegrityError:
                # Solo es "duplicado" si la fila que viola la restricción es
                # justo la de (colaborador, periodo); cualquier otra
                # IntegrityError (p.ej. una FK rota) es un error real distinto
                # y no debe enmascararse como un resultado de negocio normal.
                if Inscripcion.objects.filter(colaborador=colaborador, periodo=periodo_bloqueado).exists():
                    return InscripcionDuplicada()
                raise
