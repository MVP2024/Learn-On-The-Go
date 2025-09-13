from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase

from Teachers.models import Teacher

User = get_user_model()


class TeacherAdminRegistrationTests(TestCase):
    """Проверяем регистрацию модели Teacher в Django admin и основные настройки админки."""

    def test_teacher_model_registered_in_admin(self):
        """Модель Teacher должна быть зарегистрирована в админке."""
        self.assertIn(Teacher, admin.site._registry)

    def test_admin_list_display_contains_user(self):
        """Проверяем, что админ для Teacher содержит полезное поле отображения (user)."""
        model_admin = admin.site._registry.get(Teacher)
        # model_admin может быть None только если регистрация не выполнена
        self.assertIsNotNone(model_admin)
        # Проверяем, что list_display содержит 'user'
        ld = getattr(model_admin, "list_display", ())
        self.assertIn("user", ld)
