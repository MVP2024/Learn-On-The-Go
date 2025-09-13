from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UsersAdminTests(TestCase):
    """Проверки регистрации и базовых настроек admin для модели User."""

    def test_user_model_registered_in_admin(self):
        """Модель User должна быть зарегистрирована в админке."""
        self.assertIn(User, admin.site._registry)

    def test_custom_user_admin_list_display_contains_expected(self):
        """Проверяем, что CustomUserAdmin содержит верные поля list_display и search_fields."""
        ma = admin.site._registry.get(User)
        self.assertIsNotNone(ma)
        self.assertTrue(hasattr(ma, "list_display"))
        self.assertIn("email", ma.list_display)
        self.assertIn("role", ma.list_display)
        self.assertTrue(hasattr(ma, "search_fields"))
        self.assertIn("email", ma.search_fields)
