from capacitacion.models import ContenidoBloqueRespuesta, Inscripcion, ProgresoTema, ResultadoEvaluacion


class InscripcionNoEncontrada:
    pass


class ContenidoAjeno:
    pass


class IntentosAgotados:
    pass


class EvidenciaService:
    @staticmethod
    def _resolver_inscripcion_activa(colaborador, curso):
        """Inscripción no finalizada del colaborador cuyo curso coincide con el
        del contenido referenciado (plan §3: EvidenciaService.registrar_progreso,
        precondición). Si hay varias (p.ej. periodos distintos del mismo curso,
        AC3/AC16), se usa la más reciente por `inscrito_at`."""
        return Inscripcion.objects.filter(
            colaborador=colaborador, curso=curso, completado_at__isnull=True,
        ).order_by('-inscrito_at').first()

    @staticmethod
    def _tiene_alguna_inscripcion_activa(colaborador):
        return Inscripcion.objects.filter(colaborador=colaborador, completado_at__isnull=True).exists()

    @staticmethod
    def _reevaluar(inscripcion):
        from capacitacion.services.finalizacion_service import FinalizacionService

        FinalizacionService.reevaluar(inscripcion)

    @staticmethod
    def registrar_progreso(colaborador, tema, **campos):
        inscripcion = EvidenciaService._resolver_inscripcion_activa(colaborador, tema.modulo.curso)
        if inscripcion is not None:
            resultado = ProgresoTema.objects.create(inscripcion=inscripcion, tema=tema, **campos)
            EvidenciaService._reevaluar(inscripcion)
            return resultado

        if EvidenciaService._tiene_alguna_inscripcion_activa(colaborador):
            return ContenidoAjeno()
        return InscripcionNoEncontrada()

    @staticmethod
    def registrar_resultado_evaluacion(colaborador, evaluacion, **campos):
        curso = evaluacion.curso or evaluacion.modulo.curso
        inscripcion = EvidenciaService._resolver_inscripcion_activa(colaborador, curso)
        if inscripcion is not None:
            intentos_usados = ResultadoEvaluacion.objects.filter(
                inscripcion=inscripcion, evaluacion=evaluacion,
            ).count()
            if intentos_usados >= evaluacion.intentos_maximos:
                return IntentosAgotados()

            resultado = ResultadoEvaluacion.objects.create(inscripcion=inscripcion, evaluacion=evaluacion, **campos)
            EvidenciaService._reevaluar(inscripcion)
            return resultado

        if EvidenciaService._tiene_alguna_inscripcion_activa(colaborador):
            return ContenidoAjeno()
        return InscripcionNoEncontrada()

    @staticmethod
    def registrar_respuesta_bloque(colaborador, bloque, opcion, **campos):
        if opcion.bloque_id != bloque.id:
            return ContenidoAjeno()

        inscripcion = EvidenciaService._resolver_inscripcion_activa(colaborador, bloque.tema.modulo.curso)
        if inscripcion is not None:
            resultado = ContenidoBloqueRespuesta.objects.create(
                inscripcion=inscripcion, bloque=bloque, opcion_seleccionada=opcion,
                es_correcta=opcion.es_correcta,
            )
            EvidenciaService._reevaluar(inscripcion)
            return resultado

        if EvidenciaService._tiene_alguna_inscripcion_activa(colaborador):
            return ContenidoAjeno()
        return InscripcionNoEncontrada()
