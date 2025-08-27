from django.apps import AppConfig


class DisciplinesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Disciplines"

    def ready(self):
        import Disciplines.signals  # noqa: F401