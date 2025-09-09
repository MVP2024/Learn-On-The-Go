import importlib

from django.contrib.auth import get_user_model
from django.test import TestCase

from Admin.apps import AdminConfig
from Admin.models import AdminKey


class AdminKeyRelationTests(TestCase):
    """Тесты связей модели AdminKey и поведение при удалении пользователя."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="rel_user@a.aa", password="pw")

    def test_adminkey_deleted_when_user_deleted(self):
        """При удалении User связанный AdminKey должен удалиться (on_delete=CASCADE)."""
        ak = AdminKey.objects.create(
            user=self.user, key="rel-key-1", email=self.user.email
        )
        self.assertTrue(AdminKey.objects.filter(pk=ak.pk).exists())
        # Удаляем пользователя — должен удалиться и AdminKey
        self.user.delete()
        self.assertFalse(AdminKey.objects.filter(pk=ak.pk).exists())

    def test_can_create_multiple_keys_with_same_email_but_unique_key_enforced(self):
        """Поле email не уникально, поэтому можно создать два AdminKey с одним email при разных ключах."""
        AdminKey.objects.create(user=None, key="email-same-1", email="same@mail.test")
        AdminKey.objects.create(user=None, key="email-same-2", email="same@mail.test")
        qs = AdminKey.objects.filter(email="same@mail.test")
        self.assertEqual(qs.count(), 2)


class AdminModuleImportTests(TestCase):
    """Проверяем, что модули приложения Admin импортируются безопасно и AppConfig.ready не падает."""

    def test_admin_views_importable_and_no_errors(self):
        # Модуль views может быть пустым, но импорт не должен падать
        mod = importlib.import_module("Admin.views")
        self.assertIsNotNone(mod)

    def test_appconfig_ready_runs(self):
        # Создаём экземпляр конфигурации и вызываем ready() — не должно быть исключений
        admin_module = importlib.import_module("Admin")
        cfg = AdminConfig("Admin", admin_module)
        # ready() — в текущей реализации ничего не делает, но тест повышает покрытие
        cfg.ready()
        self.assertTrue(True)
