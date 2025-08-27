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
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Кастомная форма для изменения существующего пользователя через админку.
    Включает поле 'role'.
    """
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'patronymic', 'date_of_birth', 'phone_number', 'avatar', 'role', 'is_admin_key_required', 'has_logged_in_with_key', # Добавляем новое поле
            'groups', 'groups', 'user_permissions')
        field_classes = {'email': forms.EmailField}
