from django.contrib.auth import get_user_model
from django.test import TestCase

from Users.forms import CustomUserChangeForm, CustomUserCreationForm

User = get_user_model()


class UsersFormsTests(TestCase):
    """Проверяем формы из Users.forms."""

    def test_custom_user_creation_form_password_mismatch(self):
        """Если пароли не совпадают — форма должна быть невалидной и дать ошибку."""
        data = {
            "email": "formtest@a.aa",
            "password": "one",
            "password2": "two",
            "first_name": "Иван",
            "last_name": "Тест",
        }
        form = CustomUserCreationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors or {})

    def test_custom_user_creation_form_save_sets_password(self):
        """Метод save() должен установить пароль через set_password()."""
        data = {
            "email": "formok@a.aa",
            "password": "strongpw",
            "password2": "strongpw",
        }
        form = CustomUserCreationForm(data=data)
        self.assertTrue(form.is_valid(), msg=str(form.errors))
        user = form.save()
        self.assertTrue(user.check_password("strongpw"))

    def test_custom_user_change_form_allows_change(self):
        """CustomUserChangeForm должен корректно валидировать существующего пользователя."""
        u = User.objects.create_user(email="change@a.aa", password="pw")
        form = CustomUserChangeForm(instance=u, data={"email": u.email})
        self.assertTrue(form.is_valid(), msg=str(form.errors))
