from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Payment, PurchasedContent


@receiver(post_save, sender=Payment)
def create_purchased_content_on_payment_completion(sender, instance, created, **kwargs):
    """
    Создаёт PurchasedContent если платеж завершён и запись ещё не создана.
    Идемпотентно: get_or_create предотвращает дубли.

    Поведение:
    - Если платеж имеет статус 'completed' — создаём запись PurchasedContent.
      Это происходит как при создании платежа (created==True), так и при последующих обновлениях,
      чтобы покрыть сценарии, когда статус меняется извне (например, через webhook).
    - Используем get_or_create для защиты от гонок/дублирования.
    """
    if instance.status == "completed":
        PurchasedContent.objects.get_or_create(
            payment=instance,
            defaults={
                "user": instance.user,
                "discipline": instance.discipline,
                "lesson": instance.lesson,
            },
        )
