from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Admin.models import AdminKey


class AdminKeySerializer(serializers.ModelSerializer):
    """Сериализатор для модели AdminKey. Дополнительное поле user_email упрощает отображение."""

    user_email = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AdminKey
        fields = [
            "id",
            "user",
            "user_email",
            "key",
            "email",
            "is_active",
            "created_at",
            "expires_at",
        ]
        read_only_fields = ["id", "created_at"]

    @extend_schema_field(serializers.EmailField(allow_null=True))
    def get_user_email(self, obj):
        return obj.user.email if obj.user else obj.email
