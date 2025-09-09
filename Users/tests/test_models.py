from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    """Тесты поведения модели User и её менеджера."""

    def test_create_user_without_email_raises(self):
        """Попытка создать пользователя без email должна привести к ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_user(email=None, password="pw")

    def test_create_superuser_requires_flags(self):
        """create_superuser должен требовать is_staff/is_superuser True — если передать False, поднять ValueError."""
        with self.assertRaises(ValueError):
            # Передаём явно is_staff=False чтобы вызвать проверку и ошибку
            User.objects.create_superuser(
                email="su@example.com",
                password="pw",
                is_staff=False,
                is_superuser=False,
            )

    def test_full_name_and_str_and_natural_key(self):
        """Проверяем full_name, __str__ и natural_key при разных комбинациях полей."""
        u1 = User.objects.create_user(
            email="u1@example.com", password="pw", first_name="Иван", last_name="Иванов"
        )
        self.assertEqual(u1.full_name, "Иван Иванов")
        self.assertIn("u1@example.com", str(u1))
        self.assertEqual(u1.natural_key(), (u1.email,))

        # если имя/фамилия пустые — full_name возвращает email
        u2 = User.objects.create_user(email="nousername@example.com", password="pw")
        u2.first_name = ""
        u2.last_name = ""
        u2.save()
        self.assertEqual(u2.full_name, u2.email)

    def test_username_field_removed(self):
        """Проверяем, что в модели действительно нет username (используем email)."""
        # Атрибут username на уровне модели должен быть None (переопределён)
        self.assertIsNone(getattr(User, "username", None))
