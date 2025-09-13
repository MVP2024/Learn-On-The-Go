from django import forms
from django.contrib.auth.forms import UserChangeForm

from .models import User


class CustomUserCreationForm(forms.ModelForm):
    """
    Кастомная форма для создания нового пользователя через админку.
    Включает поле 'role'.
    """

    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Повторите пароль")
    # Делать роль необязательной в формах админки/тестах — в коде по умолчанию будет установлена 'student'
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, required=False)

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "patronymic",
            "date_of_birth",
            "phone_number",
            "avatar",
            "role",
            "is_admin_key_required",
            "has_logged_in_with_key",
            "groups",
            "user_permissions",
        )
        field_classes = {"email": forms.EmailField}

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise forms.ValidationError("Пароли не совпадают.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        # Установим роль по умолчанию, если не указана
        role = self.cleaned_data.get("role")
        if role:
            user.role = role
        else:
            user.role = getattr(user, "role", "student")
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Обычная форма для изменения существующего пользователя через админку.
    Включает поле 'role'.
    """

    # Роль необязательна при редактировании через форму
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, required=False)

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "patronymic",
            "date_of_birth",
            "phone_number",
            "avatar",
            "role",
            "is_admin_key_required",
            "has_logged_in_with_key",
            "groups",
            "user_permissions",
        )
        field_classes = {"email": forms.EmailField}
