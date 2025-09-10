from django.apps import AppConfig


class AdminConfig(AppConfig):
    """
    Настройки конфигурации приложения "Admin".
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "Admin"
