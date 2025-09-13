from typing import Any, Optional

from rest_framework import serializers
from rest_framework.viewsets import GenericViewSet

from Disciplines.models import Discipline
from Lessons.models import Lesson


class OwnerCreateMixin:
    """
    Миксин для ViewSet'ов. Централизует логику назначения owner при создании объектов.

    Правила:
    - Только преподаватель (teacher) становится владельцем создаваемого объекта (owner=user).
      Преподаватель может создавать объекты только в рамках своих дисциплин/уроков.
    - Администраторы (группа 'admin') и суперпользователь создают объекты без привязки к себе (owner=None).
    - Модераторы могут создавать объекты без владельца, но только для дисциплин/уроков без owner или для своих.
    - Остальные пользователи не имеют права создавать объекты.
    """

    # Для линтеров/типизации: request будет установлен DRF при обработке запроса
    request: Any

    @staticmethod
    def _get_related_instance(value, model_cls) -> Optional[object]:
        """
        Если value — экземпляр модели, возвращаем его.
        Если value — PK/ID (int/str), пытаемся получить объект из БД по pk.
        Если не получается — возвращаем None.
        """
        if value is None:
            return None
        if isinstance(value, model_cls):
            return value
        try:
            return model_cls.objects.get(pk=value)
        except (model_cls.DoesNotExist, ValueError, TypeError):
            return None

    def perform_create(self, serializer):
        """
        Выполняется при создании объекта через ViewSet.
        Логика описана в докстринге класса.
        """
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            raise serializers.ValidationError(
                "Аутентификация обязательна для создания объекта."
            )

        discipline_val = serializer.validated_data.get("discipline")
        lesson_val = serializer.validated_data.get("lesson")
        discipline = self._get_related_instance(discipline_val, Discipline)
        lesson = self._get_related_instance(lesson_val, Lesson)

        is_teacher = user.groups.filter(name="teacher").exists()
        is_admin_group = user.groups.filter(name="admin").exists()
        is_moderator = user.groups.filter(name="moderator").exists()
        is_super = user.is_superuser

        # Преподаватели: становятся владельцами; могут создавать только для своих дисциплин/уроков
        if is_teacher:
            discipline_owner = getattr(discipline, "owner", None)
            if (
                discipline is not None
                and discipline_owner
                and discipline_owner != user
                and not (is_super or is_admin_group)
            ):
                raise serializers.ValidationError(
                    "Вы можете создавать объекты только для своих дисциплин."
                )
            if lesson is not None:
                lesson_owner = getattr(lesson, "owner", None)
                if (
                    lesson_owner
                    and lesson_owner != user
                    and not (is_super or is_admin_group)
                ):
                    raise serializers.ValidationError(
                        "Вы можете создавать объекты только для своих уроков."
                    )
            serializer.save(owner=user)
            return

        # Модераторы: создают без owner, но только для дисциплин/уроков без owner или своих
        if is_moderator:
            discipline_owner = getattr(discipline, "owner", None)
            if (
                discipline is not None
                and discipline_owner
                and discipline_owner != user
                and not (is_super or is_admin_group)
            ):
                raise serializers.ValidationError(
                    "Модератор может создавать объекты только для дисциплин без владельца или для своих дисциплин."
                )
            if lesson is not None:
                lesson_owner = getattr(lesson, "owner", None)
                if (
                    lesson_owner
                    and lesson_owner != user
                    and not (is_super or is_admin_group)
                ):
                    raise serializers.ValidationError(
                        "Модератор может создавать объекты только для уроков без владельца или для своих уроков."
                    )
            serializer.save(owner=None)
            return

        # Админы и суперпользователь: создают объекты без привязки к ним (owner=None)
        if is_super or is_admin_group:
            serializer.save(owner=None)
            return

        # Остальные — не имеют прав
        raise serializers.ValidationError("У вас нет прав для создания этого объекта.")


class TitleOrPkLookupMixin(GenericViewSet):
    """
    Миксин для ViewSet'ов: поддерживает lookup по slug/title (строка) и по pk (число).

    Поведение:
    - Если в path передан непустой нечисловой сегмент — пытаемся найти объект по slug,
      затем по title__iexact.
      - Если найден 1 объект — возвращаем его.
      - Если найдено >1 — можно уточнить через query param ?id=<pk> или ?pk=<pk>.
      - Если уточнения нет — бросаем ValidationError с инструкцией.
    - Если path-сегмент числовой — пробуем получить по pk.
    - В остальных случаях вызывается стандартный super().get_object().

    Требования: queryset должен быть определён в ViewSet.
    """

    def get_object(self):
        lookup_url_kwarg = getattr(self, "lookup_url_kwarg", None) or self.lookup_field
        lookup = self.kwargs.get(lookup_url_kwarg)
        # fallback: try common alternative 'id' if lookup wasn't found
        if lookup is None and lookup_url_kwarg != "id":
            lookup = self.kwargs.get("id")
        if lookup is None:
            return super().get_object()
        # noinspection PyBroadException
        try:
            lookup_str = str(lookup)
        except Exception:
            return super().get_object()
        qs = self.filter_queryset(self.get_queryset())
        # Если lookup не числовой — пробуем сначала slug, затем поиск по title (iexact)
        if not lookup_str.isdigit():
            # try slug first (unique, fast)
            # noinspection PyBroadException
            try:
                obj = qs.get(slug=lookup_str)
                self.check_object_permissions(self.request, obj)
                return obj
            except Exception:
                pass

            matches = qs.filter(title__iexact=lookup_str)
            match_count = matches.count()
            if match_count == 1:
                obj = matches.first()
                self.check_object_permissions(self.request, obj)
                return obj
            if match_count > 1:
                request = getattr(self, "request", None)
                id_param = None
                if request is not None:
                    id_param = request.query_params.get(
                        "id"
                    ) or request.query_params.get("pk")
                if id_param:
                    try:
                        pk_val = int(id_param)
                    except Exception:
                        raise serializers.ValidationError(
                            "Параметр id должен быть числом (pk)."
                        )
                    try:
                        obj = matches.get(pk=pk_val)
                        self.check_object_permissions(self.request, obj)
                        return obj
                    except matches.model.DoesNotExist:
                        from rest_framework.exceptions import NotFound

                        raise NotFound(
                            f"Объект с id={pk_val} и title='{lookup_str}' не найден среди совпадений."
                        )
                raise serializers.ValidationError(
                    "Найдено несколько объектов с таким названием. Уточните запрос, добавив ?id=<pk> или используйте ID в пути."
                )
        # Если lookup — число, пробуем по pk
        if lookup_str.isdigit():
            # noinspection PyBroadException
            try:
                pk_val = int(lookup_str)
            except Exception:
                return super().get_object()
            # noinspection PyBroadException
            try:
                obj = qs.get(pk=pk_val)
                self.check_object_permissions(self.request, obj)
                return obj
            except Exception:
                pass
        return super().get_object()
