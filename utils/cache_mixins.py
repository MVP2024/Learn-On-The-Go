from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

class RetrieveCacheMixin:
    """
    Миксин для кэширования действия 'retrieve' в ModelViewSet.
    """
    @method_decorator(cache_page(60 * 15)) # Кэшировать 15 минут
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)