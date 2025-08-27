from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from Users.forms import CustomUserChangeForm, CustomUserCreationForm
from Users.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Кастомизация админки для модели User.
    Добавляет поля patronymic, date_of_birth, phone_number, avatar,
    а также флаги is_admin_key_required и has_logged_in_with_key.
    """

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    # "UserAdmin.list_display +" добавить после "="
    list_display = (
        "email",
        "first_name",
        "last_name",
        "phone_number",
        "date_of_birth",
        "role",
        "is_admin_key_required",
        "has_logged_in_with_key",
        "is_active",
    )
    # Переопределяем search_fields
    search_fields = ("email", "first_name", "last_name", "phone_number")
    # сортировка
    ordering = ("email", "last_name", "role")

    # Расширяем fieldsets для добавления наших полей
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "patronymic",
                    "date_of_birth",
                    "phone_number",
                    "avatar",
                    "role",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                    "is_admin_key_required",
                    "has_logged_in_with_key",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Расширяем add_fieldsets для добавления наших полей
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password", "password2"),
            },
        ),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "patronymic",
                    "date_of_birth",
                    "phone_number",
                    "avatar",
                    "role",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                    "is_admin_key_required",
                    "has_logged_in_with_key",
                )
            },
        ),
    )
