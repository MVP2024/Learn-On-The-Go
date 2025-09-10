from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class RetrieveCacheMixin:
    """
    Миксин для кэширования действия 'retrieve' в ModelViewSet.
    """

    @method_decorator(cache_page(60 * 15))  # Кэшировать 15 минут
    def retrieve(self, request, *args, **kwargs):
        base_retrieve = getattr(super(), "retrieve", None)
        if base_retrieve is None:
            # Если базовый класс не содержит retrieve — возвращаем 404-пустой ответ
            # или можно поднять AttributeError; оставим поведение более безопасным.
            from rest_framework import status
            from rest_framework.response import Response

            return Response(status=status.HTTP_404_NOT_FOUND)
        return base_retrieve(request, *args, **kwargs)
