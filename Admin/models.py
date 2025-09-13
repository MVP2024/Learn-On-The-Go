from django.db import models
from django.db.models import Q

from Users.models import User


class AdminKey(models.Model):
    """
    Модель для хранения уникальных административных ключей, привязанных к пользователям.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="admin_key",
        verbose_name="Пользователь",
        null=True,
        blank=True,
    )
    key = models.CharField(
        max_length=64, unique=True, verbose_name="Административный ключ"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    expires_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата истечения"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    # Добавляем поле для привязки ключа к email, если потребуется для генерации
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email для ключа",
        help_text="Email, на который был отправлен ключ (для удобства)",
    )

    def __str__(self):
        user_email = self.user.email if self.user else (self.email or "—")
        return f"Ключ для {user_email} (активен: {self.is_active})"

    class Meta:
        verbose_name = "Административный ключ"
        verbose_name_plural = "Административные ключи"
        ordering = ["-created_at"]
        indexes = [
            # Индекс по expires_at только для активных ключей — ускоряет поиск просроченных
            models.Index(
                fields=["expires_at"],
                name="adminkey_expires_idx",
                condition=Q(is_active=True),
            ),
        ]
