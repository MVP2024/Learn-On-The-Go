from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from Admin.models import AdminKey


class AdminKeyModelTests(TestCase):
    """Тесты для модели AdminKey: создание, строковое представление и уникальность ключа."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="ak_user@a.aa", password="pw")

    def test_create_adminkey_with_user_and_email(self):
        ak = AdminKey.objects.create(
            user=self.user, key="uniq-key-1", email=self.user.email
        )
        self.assertEqual(ak.user, self.user)
        # __str__ должен содержать email
        s = str(ak)
        self.assertIn(self.user.email, s)
        self.assertIn("активен", s)

    def test_create_adminkey_without_user_but_with_email(self):
        ak = AdminKey.objects.create(user=None, key="uniq-key-2", email="nobody@x.y")
        self.assertIsNone(ak.user)
        self.assertEqual(ak.email, "nobody@x.y")
        self.assertIn("nobody@x.y", str(ak))

    def test_unique_key_constraint_raises_integrityerror(self):
        AdminKey.objects.create(user=self.user, key="dup-key", email=self.user.email)
        with self.assertRaises(IntegrityError):
            # Попытка создать с тем же ключом должна упасть
            AdminKey.objects.create(user=None, key="dup-key", email="other@x.y")


class AdminRegistrationTests(TestCase):
    """Проверяем регистрацию модели AdminKey в Django admin и базовую конфигурацию AdminKeyAdmin."""

    def test_adminkey_registered_in_admin(self):
        # Модель должна быть зарегистрирована в админке
        self.assertIn(AdminKey, admin.site._registry)

    def test_adminkey_admin_has_expected_options(self):
        ma = admin.site._registry.get(AdminKey)
        self.assertIsNotNone(ma)
        # проверяем, что перечисленные поля присутствуют в list_display
        for fld in ("user", "key", "email", "is_active", "created_at", "expires_at"):
            self.assertIn(fld, getattr(ma, "list_display", ()))
        # readonly_fields должен содержать created_at
        self.assertIn("created_at", getattr(ma, "readonly_fields", ()))
        # search_fields как минимум должен включать key/email
        self.assertTrue(hasattr(ma, "search_fields"))
        self.assertIn("key", ma.search_fields)
