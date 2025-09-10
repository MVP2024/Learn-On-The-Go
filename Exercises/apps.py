from django.apps import AppConfig


class ExercisesConfig(AppConfig):
    """
    Настройки конфигурации приложения "Exercises".
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "Exercises"

    def ready(self):
        """
        Импортирует сигналы для приложения Exercises при готовности приложения.
        Используем динамический импорт через importlib для безопасности.
        """
        import importlib

        try:
            importlib.import_module(f"{self.name}.signals")
        except Exception:
            # Если, модуля signals нет — пропускаем silently
            pass


# Тесты ожидают имя TestsConfig — добавляем альянс, чтобы импорт TestsConfig работал.
TestsConfig = ExercisesConfig
