from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Discipline


@receiver(post_save, sender=Discipline)
def clear_discipline_cache_on_save(sender, instance, **kwargs):
    """
    Очищает кэш для конкретной дисциплины после ее сохранения.
    """
    cache.delete(f"/disciplines/{instance.pk}/")


@receiver(post_delete, sender=Discipline)
def clear_discipline_cache_on_delete(sender, instance, **kwargs):
    """
    Очищает кэш для конкретной дисциплины после ее удаления.
    """
    cache.delete(f"/disciplines/{instance.pk}/")
