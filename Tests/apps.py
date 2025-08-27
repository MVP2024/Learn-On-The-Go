"""
Конфигурация приложения Tests.
"""
from django.apps import AppConfig

class TestsConfig(AppConfig):
    """
    Настройки конфигурации приложения "Tests".
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "Tests"

    def ready(self):
        """
        Импортирует сигналы для приложения Tests при готовности приложения.
        """
        from Tests import signals