from .base import BaseCatalogo


class NivelCompetencia(BaseCatalogo):
    """
    Catálogo compartido por CompetenciaCurso y CompetenciaPuesto.
    Ejemplos de codigo: desarrolla, refuerza, introduce, requerida, deseable, complementaria.
    Lookups siempre por `codigo`, nunca por `nombre`.
    """

    class Meta(BaseCatalogo.Meta):
        verbose_name = 'Nivel de competencia'
        verbose_name_plural = 'Niveles de competencia'
