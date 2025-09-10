from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from Disciplines.common_permissions import (
    IsOwnerOrAdminOrModerator,
    IsTeacherOrAdminOrModerator,
)
from Users.permissions import IsModerator, IsStudent
from utils.cache_mixins import RetrieveCacheMixin
from utils.common_mixins import OwnerCreateMixin, TitleOrPkLookupMixin
from utils.paginators import StandardResultsSetPagination

from .models import Lesson, UserLessonProgress
from .serializers import LessonSerializer, UserLessonProgressSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Список уроков",
        description=(
            "Возвращает список уроков с возможностью фильтрации и пагинации."
            " Параметры фильтра: title (partial), description (partial), discipline__title (partial)."
        ),
        parameters=[
            OpenApiParameter(
                name="title",
                type=str,
                location="query",
                description="Поиск по названию урока (частичное совпадение)",
            ),
            OpenApiParameter(
                name="description",
                type=str,
                location="query",
                description="Поиск по описанию урока (частичное совпадение)",
            ),
            OpenApiParameter(
                name="discipline__title",
                type=str,
                location="query",
                description="Поиск по названию дисциплины (частичное совпадение)",
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location="query",
                description="Поле для сортировки: lesson_order, -lesson_order, title, -title, created_at, -created_at",
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location="query",
                description="Номер страницы (пагинация)",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location="query",
                description="Размер страницы (пагинация)",
            ),
        ],
        responses={200: LessonSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Получить урок по ID или названию",
        description="Возвращает детали конкретного урока по ID (число) или точному названию (строка).",
    ),
    create=extend_schema(
        summary="Создать урок",
        description="Создаёт новый урок (доступно учителям/админам/модераторам).",
        request=LessonSerializer,
        responses={201: LessonSerializer},
        examples=[
            OpenApiExample(
                "JSON — создание урока по video_url",
                value={
                    "title": "Краткая история развития биологии",
                    "description": "В этом уроке узнаем, как зарождалась биология как наука о жизни.",
                    "discipline": "matematika_7",  # <- указывайте slug дисциплины или её числовой ID
                    "section": "Глава №1",
                    "video_url": "https://rutube.ru/video/789811ec140f43a9c96311cee4bb0a10/",
                    "lesson_order": 1,
                },
                request_only=True,
                media_type="application/json",
            ),
            OpenApiExample(
                "multipart/form-data — загрузка видео и preview",
                value={
                    "title": "Краткая история развития биологии",
                    "description": "В этом уроке узнаем, как зарождалась биология как наука о жизни.",
                    "discipline": "matematika_7",  # <- указывайте slug дисциплины или её числовой ID
                    "section": "Глава №1",
                    "lesson_order": 1,
                    "video_file": "<выберите файл>",
                    "preview": "<выберите изображение>",
                },
                request_only=True,
                media_type="multipart/form-data",
            ),
        ],
    ),
    update=extend_schema(
        summary="Обновить урок",
        description="Полное обновление урока (требует всех полей).",
        request=LessonSerializer,
        responses={200: LessonSerializer},
    ),
    partial_update=extend_schema(
        summary="Частично обновить урок",
        description="Частичное обновление полей урока.",
        request=LessonSerializer,
        responses={200: LessonSerializer},
    ),
    destroy=extend_schema(
        summary="Удалить урок",
        description="Удаляет урок (только владелец/модератор/админ).",
    ),
)
@extend_schema(tags=["Уроки"])
class LessonViewSet(
    OwnerCreateMixin, TitleOrPkLookupMixin, RetrieveCacheMixin, viewsets.ModelViewSet
):
    """
    Тут работаем с уроками - создаем, смотрим, редактируем.
    """

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "title": ["icontains"],
        "description": ["icontains"],
        "discipline__title": ["icontains"],
    }
    lookup_field = "pk"
    lookup_value_regex = r"[^/]+"

    def get_permissions(self):
        if self.action in ["create"]:
            self.permission_classes = [IsAuthenticated & IsTeacherOrAdminOrModerator]
        elif self.action in ["update", "partial_update", "destroy"]:
            self.permission_classes = [
                IsAuthenticated & (IsOwnerOrAdminOrModerator | IsModerator)
            ]
        elif self.action in ["list", "retrieve"]:
            self.permission_classes = [IsAuthenticated]
        elif self.action in ["update_progress", "get_progress"]:
            self.permission_classes = [IsAuthenticated, IsStudent]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.groups.filter(name="teacher").exists() and not (
                user.is_superuser
                or user.groups.filter(name="admin").exists()
                or user.groups.filter(name="moderator").exists()
            ):
                queryset = Lesson.objects.filter(
                    discipline__owner=user
                ) | Lesson.objects.filter(discipline__owner__isnull=True, owner=user)
            else:
                queryset = Lesson.objects.all()
            order_by = self.request.query_params.get("order_by", "lesson_order")
            if order_by == "title":
                queryset = queryset.order_by("title")
            elif order_by == "-title":
                queryset = queryset.order_by("-title")
            elif order_by == "created_at":
                queryset = queryset.order_by("created_at")
            elif order_by == "-created_at":
                queryset = queryset.order_by("-created_at")
            elif order_by == "lesson_order":
                queryset = queryset.order_by("lesson_order")
            elif order_by == "-lesson_order":
                queryset = queryset.order_by("-lesson_order")
            else:
                queryset = queryset.order_by("lesson_order", "title")
            return queryset
        return Lesson.objects.none()

    @extend_schema(
        summary="Поиск уроков по названию",
        description=(
            "Поиск уроков по точному названию (case-insensitive) или частичному совпадению (icontains) при exact=false."
        ),
        parameters=[
            OpenApiParameter(
                name="title",
                type=str,
                location="query",
                description="Название урока",
                required=True,
            ),
            OpenApiParameter(
                name="exact",
                type=bool,
                location="query",
                description="Точное совпадение (default: true)",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location="query",
                description="Номер страницы (пагинация)",
                required=False,
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location="query",
                description="Размер страницы (пагинация)",
                required=False,
            ),
        ],
        responses={200: LessonSerializer(many=True)},
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

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Обновить прогресс урока",
        description=(
            "Обновляет прогресс просмотра урока для текущего пользователя (студента). "
            "Принимает `watched_duration` (сколько секунд просмотрено) и/или `is_completed` (флаг завершения урока)."
        ),
        parameters=[
            OpenApiParameter(
                name="pk",
                type=str,
                location="path",
                description="ID урока (число) или название урока (строка)",
            ),
        ],
        request={
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "watched_duration": {
                            "type": "integer",
                            "description": "Просмотрено секунд",
                        },
                        "is_completed": {
                            "type": "boolean",
                            "description": "Урок пройден (true/false)",
                        },
                    },
                }
            }
        },
        responses={
            200: UserLessonProgressSerializer,
            404: {"description": "Прогресс для этого урока не найден."},
        },
        examples=[
            OpenApiExample(
                "Пример обновления прогресса (JSON)",
                value={"watched_duration": 120, "is_completed": True},
                request_only=True,
                media_type="application/json",
            )
        ],
    )
    @action(
        detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsStudent]
    )
    def update_progress(self, request, pk=None):
        lesson = self.get_object()
        user = request.user
        watched_duration = request.data.get("watched_duration")
        is_completed = request.data.get("is_completed")
        try:
            progress = UserLessonProgress.objects.get(user=user, lesson=lesson)
        except UserLessonProgress.DoesNotExist:
            progress = UserLessonProgress.objects.create(user=user, lesson=lesson)
        if watched_duration is not None:
            try:
                watched_duration = int(watched_duration)
            except Exception:
                return Response(
                    {"error": "watched_duration должен быть числом"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if watched_duration > progress.watched_duration:
                progress.watched_duration = watched_duration
            progress.current_time = watched_duration
            if (
                hasattr(lesson, "duration_seconds")
                and lesson.duration_seconds
                and progress.watched_duration >= lesson.duration_seconds
            ):
                progress.is_completed = True
        if is_completed is not None:
            progress.is_completed = bool(is_completed)
        progress.save()
        serializer = UserLessonProgressSerializer(progress)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Получить прогресс урока",
        description="Получает прогресс просмотра урока для текущего пользователя (студента).",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=str,
                location="path",
                description="ID урока (число) или название урока (строка)",
            ),
        ],
        responses={
            200: UserLessonProgressSerializer,
            404: {"description": "Прогресс для этого урока не найден."},
        },
    )
    @action(
        detail=True, methods=["get"], permission_classes=[IsAuthenticated, IsStudent]
    )
    def get_progress(self, request, pk=None):
        lesson = self.get_object()
        user = request.user
        try:
            progress = UserLessonProgress.objects.get(user=user, lesson=lesson)
            serializer = UserLessonProgressSerializer(progress)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserLessonProgress.DoesNotExist:
            return Response(
                {"detail": "Прогресс для этого урока не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )
