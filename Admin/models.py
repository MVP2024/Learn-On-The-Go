from django.db import models
from Users.models import User


class AdminKey(models.Model):
    """
    Модель для хранения уникальных административных ключей, привязанных к пользователям.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin_key',
        verbose_name="Пользователь"
    )
    key = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Административный ключ"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата истечения"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен"
    )
    # Добавляем поле для привязки ключа к email, если потребуется для генерации
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email для ключа",
        help_text="Email, на который был отправлен ключ (для удобства)"
    )

    def __str__(self):
        return f"Ключ для {self.user.email} (активен: {self.is_active})"

    class Meta:
        verbose_name = "Административный ключ"
        verbose_name_plural = "Административные ключи"
