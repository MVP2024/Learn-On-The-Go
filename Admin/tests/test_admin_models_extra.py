from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from Admin.models import AdminKey


class AdminKeyExtraModelTests(TestCase):
    """Дополнительные тесты для модели AdminKey: ограничения OneToOne, __str__ и поля expires_at."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="extra_user@a.aa", password="pw")

    def test_one_to_one_constraint_on_user_raises_integrityerror(self):
        """Попытка создать второй AdminKey для того же User должна привести к IntegrityError."""
        AdminKey.objects.create(
            user=self.user, key="user-uniq-1", email=self.user.email
        )
        with self.assertRaises(IntegrityError):
            # Второй ключ для того же user -> нарушение OneToOne
            AdminKey.objects.create(
                user=self.user, key="user-uniq-2", email=self.user.email
            )

    def test_str_inactive_contains_false(self):
        """Проверяем, что строковое представление отражает флаг is_active (False)."""
        ak = AdminKey.objects.create(
            user=self.user, key="inactive-key", email=self.user.email, is_active=False
        )
        s = str(ak)
        self.assertIn(self.user.email, s)
        self.assertIn("активен", s)
        # Проверяем явно, что значение False присутствует
        self.assertIn("False", s)

    def test_create_without_user_and_without_email_shows_dash_in_str(self):
        """Если ни user ни email не заданы — __str__ должен показывать знак "—" для email."""
        ak = AdminKey.objects.create(user=None, key="no-one-key", email=None)
        s = str(ak)
        self.assertIn("—", s)
        self.assertIn("активен", s)

    def test_expires_at_field_is_stored_and_readable(self):
        """Проверяем, что поле expires_at можно установить и оно хранится."""
        future = timezone.now() + timedelta(days=7)
        ak = AdminKey.objects.create(
            user=None, key="exp-key", email="e@x.y", expires_at=future
        )
        self.assertIsNotNone(ak.expires_at)
        self.assertEqual(
            ak.expires_at.replace(microsecond=0), future.replace(microsecond=0)
        )
