"""
Конфигурация приложения Lessons.
"""
from django.apps import AppConfig


class LessonsConfig(AppConfig):
    """
    Настройки конфигурации приложения "Lessons".
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "Lessons"

    def ready(self):
        """
        Импортирует сигналы для приложения Lessons при готовности приложения.
        """
        import Lessons.signals  # noqa: F401
