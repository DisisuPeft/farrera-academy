from django.apps import AppConfig


class CompetenciasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'competencias'
    verbose_name = 'Competencias'

    def ready(self):
        import competencias.signals  # noqa: F401
