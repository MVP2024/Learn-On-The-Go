from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Test

@receiver(post_save, sender=Test)
def clear_test_cache_on_save(sender, instance, **kwargs):
    """
    Очищает кэш для конкретного теста после его сохранения.
    """
    cache.delete(f"/tests/{instance.pk}/")

@receiver(post_delete, sender=Test)
def clear_test_cache_on_delete(sender, instance, **kwargs):
    """
    Очищает кэш для конкретного теста после его удаления.
    """
    cache.delete(f"/tests/{instance.pk}/")
