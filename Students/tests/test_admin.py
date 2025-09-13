from django.contrib import admin
from django.test import TestCase

import Students.admin  # noqa: F401
from Students.models import Student


class StudentAdminTests(TestCase):
    """Проверки конфигурации админки для модели Student."""

    def test_student_model_registered_in_admin(self):
        """Убедимся, что модель Student зарегистрирована в админке."""
        self.assertIn(Student, admin.site._registry)

    def test_student_admin_list_display_and_search(self):
        """Проверяем, что у StudentAdmin настроены list_display, search_fields и list_filter."""
        ma = admin.site._registry.get(Student)
        # Проверяем набор полей для отображения
        self.assertTrue(hasattr(ma, "list_display"))
        self.assertIn("user", ma.list_display)
        self.assertIn("course", ma.list_display)
        # Проверяем поля поиска
        self.assertTrue(hasattr(ma, "search_fields"))
        self.assertIn("user__email", ma.search_fields)
        self.assertIn("user__first_name", ma.search_fields)
        # Проверяем фильтр
        self.assertTrue(hasattr(ma, "list_filter"))
        self.assertIn("course", ma.list_filter)
