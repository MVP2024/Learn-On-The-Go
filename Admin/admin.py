from django.contrib import admin

from Admin.models import AdminKey


@admin.register(AdminKey)
class AdminKeyAdmin(admin.ModelAdmin):
    """
    Админка для модели AdminKey.
    """

    list_display = ("user", "key", "email", "is_active", "created_at", "expires_at")
    search_fields = ("user__email", "key", "email")
    list_filter = ("is_active",)
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("user", "key", "email", "is_active", "expires_at")}),
    )
