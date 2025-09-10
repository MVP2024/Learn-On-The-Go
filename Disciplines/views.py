from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from Users.permissions import IsModerator
from utils.cache_mixins import RetrieveCacheMixin
from utils.common_mixins import TitleOrPkLookupMixin
from utils.paginators import StandardResultsSetPagination

from .common_permissions import IsOwnerOrAdminOrModerator, IsTeacherOrAdminOrModerator
from .models import Discipline, Section
from .serializers import DisciplineSerializer, SectionSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Список дисциплин",
        description="Возвращает список дисциплин с фильтрацией и пагинацией.",
        responses={200: DisciplineSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Детали дисциплины",
        description="Возвращает подробную информацию о дисциплине, включая информацию о цене и статусе доступа пользователя.",
        responses={200: DisciplineSerializer},
    ),
    create=extend_schema(
        summary="Создать дисциплину",
        description="Создаёт новую дисциплину. Доступно учителям/админам/модераторам.",
    ),
    update=extend_schema(
        summary="Обновить дисциплину", description="Полное обновление дисциплины."
    ),
    partial_update=extend_schema(
        summary="Частичное обновление дисциплины",
        description="Частичное обновление полей дисциплины.",
    ),
    destroy=extend_schema(
        summary="Удалить дисциплину",
        description="Удаляет дисциплину (только владелец/модератор/админ).",
    ),
)
@extend_schema(tags=["Дисциплины"])
class DisciplineViewSet(
    TitleOrPkLookupMixin, RetrieveCacheMixin, viewsets.ModelViewSet
):
    """
    Тут работаем с дисциплинами - создаем, смотрим, редактируем.
    Поведение lookup реализовано в TitleOrPkLookupMixin: сначала попытка по title (iexact), затем (при неоднозначности) опциональное уточнение ?id=<pk>, и запасной вариант — numeric pk.
    """

    queryset = Discipline.objects.all()
    serializer_class = DisciplineSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "title": ["icontains"],  # Поиск по названию - ОПЦИОНАЛЬНЫЙ
        "owner__email": ["icontains"],  # Поиск по email владельца - ОПЦИОНАЛЬНЫЙ
    }

    def get_permissions(self):
        if self.action in ["create"]:
            self.permission_classes = [IsAuthenticated & IsTeacherOrAdminOrModerator]
        elif self.action in ["update", "partial_update", "destroy"]:
            self.permission_classes = [
                IsAuthenticated & (IsOwnerOrAdminOrModerator | IsModerator)
            ]
        elif self.action in ["list", "retrieve"]:
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    @extend_schema(
        summary="Получить дисциплину по ID или названию",
        description="Возвращает детали конкретной дисциплины по ID (число) или точному названию (строка).",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=str,
                location="path",
                description="ID дисциплины (число) или название дисциплины (строка)",
            )
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Создать новую дисциплину",
        description="Создает новую дисциплину. Доступно только учителям, администраторам и модераторам.",
        examples=[
            OpenApiExample(
                "Пример создания дисциплины",
                value={
                    "title": "Математика",
                    "description": "Курс по высшей математике",
                },
                request_only=True,
                media_type="application/json",
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        if (
            user.groups.filter(name="teacher").exists()
            or user.is_superuser
            or user.groups.filter(name="admin").exists()
        ):
            serializer.save(owner=user)
        elif user.groups.filter(name="moderator").exists():
            serializer.save(owner=None)
        else:
            raise serializers.ValidationError("У вас нет прав для создания дисциплин.")

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.groups.filter(name="teacher").exists() and not (
                user.is_superuser
                or user.groups.filter(name="admin").exists()
                or user.groups.filter(name="moderator").exists()
            ):
                queryset = Discipline.objects.filter(owner=user)
            else:
                queryset = Discipline.objects.all()
            order_by = self.request.query_params.get("order_by", "title")
            if order_by == "title":
                queryset = queryset.order_by("title")
            elif order_by == "-title":
                queryset = queryset.order_by("-title")
            elif order_by == "created_at":
                queryset = queryset.order_by("created_at")
            elif order_by == "-created_at":
                queryset = queryset.order_by("-created_at")
            else:
                queryset = queryset.order_by("order", "title")
            return queryset
        return Discipline.objects.none()

    @extend_schema(
        summary="Поиск дисциплин по названию",
        description=(
            "Возвращает список дисциплин, совпадающих по названию. По умолчанию выполняется "
            "точное сравнение (case-insensitive). Если указать exact=false — будет выполнен partial search (icontains)."
        ),
        parameters=[
            OpenApiParameter(
                name="title",
                type=str,
                location="query",
                description="Название дисциплины (обязательно)",
                required=True,
            ),
            OpenApiParameter(
                name="exact",
                type=bool,
                location="query",
                description="Точное совпадение (default: true)",
                required=False,
            ),
        ],
        responses={200: DisciplineSerializer(many=True)},
    )
    @action(detail=False, methods=["get"])
    def by_title(self, request):
        title = request.query_params.get("title")
        if not title:
            return Response(
                {"error": "Параметр title обязателен."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        exact = request.query_params.get("exact", "true").lower() not in (
            "0",
            "false",
            "no",
        )
        qs = self.get_queryset()
        if exact:
            matches = qs.filter(title__iexact=title)
        else:
            matches = qs.filter(title__icontains=title)
        page = self.paginate_queryset(matches)
        if page is not None:
            serializer = self.get_serializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(
            matches, many=True, context={"request": request}
        )
        return Response(serializer.data)


@extend_schema(tags=["Разделы"])
class SectionViewSet(viewsets.ModelViewSet):
    """
    API для разделов (Section). Позволяет создавать/редактировать/удалять разделы дисциплины.
    Доступ: учитель/админ/модератор.
    """

    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated & IsTeacherOrAdminOrModerator]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "discipline__slug": ["exact", "icontains"],
        "title": ["icontains"],
    }
    pagination_class = StandardResultsSetPagination

    def perform_create(self, serializer):
        # При создании раздела удостоверимся, что дисциплина существует и пользователь имеет права
        discipline = serializer.validated_data.get("discipline")
        user = self.request.user
        # Если пользователь — учитель, проверим, что дисциплина принадлежит ему или не имеет owner
        if user.groups.filter(name="teacher").exists() and not (
            user.is_superuser or user.groups.filter(name="admin").exists()
        ):
            if getattr(discipline, "owner", None) and discipline.owner != user:
                raise serializers.ValidationError(
                    "Вы можете создавать разделы только в ваших дисциплинах."
                )
        serializer.save()

    def get_queryset(self):
        qs = Section.objects.select_related("discipline").all()
        # дополнительная фильтрация по названию дисциплины или идентификатору через параметры запроса
        discipline = self.request.query_params.get("discipline")
        if discipline:
            # сначала пробуем использовать числовой идентификатор
            if discipline.isdigit():
                qs = qs.filter(discipline__id=int(discipline))
            else:
                qs = qs.filter(discipline__slug=discipline)
        return qs
