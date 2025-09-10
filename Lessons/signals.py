from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Lesson


@receiver(post_save, sender=Lesson)
def clear_lesson_cache_on_save(sender, instance, **kwargs):
    """
    Очищает кэш для конкретного урока после его сохранения.
    """
    cache.delete(f"/lessons/{instance.pk}/")


@receiver(post_delete, sender=Lesson)
def clear_lesson_cache_on_delete(sender, instance, **kwargs):
    """
    Очищает кэш для конкретного урока после его удаления.
    """
    cache.delete(f"/lessons/{instance.pk}/")
