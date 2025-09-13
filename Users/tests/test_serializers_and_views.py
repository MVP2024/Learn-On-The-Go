from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

# from Users.models import User  # removed: используем get_user_model()
from Admin.models import AdminKey
from Users.serializers import (
    AdminKeyLoginSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
)

User = get_user_model()


class UsersSerializersTests(TestCase):
    """Тестируем сериализаторы Users: регистрация и вход по ключу."""

    def setUp(self):
        for g in ("admin", "teacher", "student", "moderator"):
            Group.objects.get_or_create(name=g)

    def test_register_serializer_creates_student_and_teacher(self):
        """RegisterSerializer должен корректно создавать студента и преподавателя, привязывая группы."""
        data = {
            "email": "new_student@a.aa",
            "password": "pass1234",
            "role": "student",
            "first_name": "Иван",
            "last_name": "Петров",
        }
        ser = RegisterSerializer(data=data)
        self.assertTrue(ser.is_valid(), msg=str(ser.errors))
        user = ser.save()
        self.assertEqual(user.email, data["email"])
        self.assertIn(Group.objects.get(name="student"), user.groups.all())

        # teacher
        data2 = {
            "email": "new_teacher@a.aa",
            "password": "pass1234",
            "role": "teacher",
            "first_name": "Пётр",
            "last_name": "Сидоров",
        }
        ser2 = RegisterSerializer(data=data2)
        self.assertTrue(ser2.is_valid(), msg=str(ser2.errors))
        user2 = ser2.save()
        self.assertIn(Group.objects.get(name="teacher"), user2.groups.all())

    def test_adminkey_login_success_and_invalid(self):
        """AdminKeyLoginSerializer должен валидировать корректный ключ и отвергать неправильный."""
        user = User.objects.create_user(email="admintest@a.aa", password="pw")
        user.role = "admin"
        user.is_admin_key_required = True
        user.save()
        AdminKey.objects.create(
            user=user, key="thekey", is_active=True, email=user.email
        )

        data = {"email": user.email, "password": "pw", "admin_key": "thekey"}
        ser = AdminKeyLoginSerializer(data=data)
        self.assertTrue(ser.is_valid(), msg=str(ser.errors))
        # после валидации сериализатор установит ser.user
        ser.validate(data)
        self.assertIsNotNone(ser.user)

        # неправильный ключ
        data2 = {"email": user.email, "password": "pw", "admin_key": "bad"}
        ser2 = AdminKeyLoginSerializer(data=data2)
        with self.assertRaises(Exception):
            ser2.is_valid(raise_exception=True)

    def test_token_obtain_serializer_uses_email_field(self):
        """Проверяем, что CustomTokenObtainPairSerializer использует email как username_field."""
        ser = CustomTokenObtainPairSerializer
        self.assertEqual(ser.username_field, "email")
