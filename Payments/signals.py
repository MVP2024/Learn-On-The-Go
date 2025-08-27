from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment, PurchasedContent


@receiver(post_save, sender=Payment)
def create_purchased_content_on_payment_completion(sender, instance, **kwargs):
    """
    Автоматически создает запись в PurchasedContent при завершении платежа.
    Этот сигнал является дополнительной защитой на случай,
    если запись не была создана в сервисе.
    """
    if instance.status == 'completed' and kwargs.get('created', False) is False:
        # Проверяем, что платеж только что стал completed (не создан как completed)
        old_instance = Payment.objects.get(pk=instance.pk)
        
        if not hasattr(old_instance, '_state') or old_instance.status != 'completed':
            # Проверяем, что еще нет записи о покупке
            if not PurchasedContent.objects.filter(payment=instance).exists():
                PurchasedContent.objects.create(
                    user=instance.user,
                    discipline=instance.discipline,
                    lesson=instance.lesson,
                    payment=instance
                )