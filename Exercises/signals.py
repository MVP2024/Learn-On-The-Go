from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Test


@receiver(post_save, sender=Test)
def clear_test_cache_on_save(sender, instance, **kwargs):
    """
    Очищает кэш для конкретного теста после его сохранения.
    """
    cache.delete(f"/exercises/{instance.pk}/")


@receiver(post_delete, sender=Test)
def clear_test_cache_on_delete(sender, instance, **kwargs):
    """
    Очищает кэш для конкретного теста после его удаления.
    """
    cache.delete(f"/exercises/{instance.pk}/")
