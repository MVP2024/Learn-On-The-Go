from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, serializers
from .models import Discipline
from .serializers import DisciplineSerializer
from .common_permissions import IsOwnerOrAdminOrModerator, IsTeacherOrAdminOrModerator
from rest_framework.permissions import IsAuthenticated
from Users.permissions import IsModerator
from utils.cache_mixins import RetrieveCacheMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from Lessons.serializers import LessonSerializer
from Tests.serializers import QuizSerializer
from utils.services import get_lessons_and_tests_for_discipline
from utils.paginators import StandardResultsSetPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample


@extend_schema(tags=['Дисциплины'])
class DisciplineViewSet(RetrieveCacheMixin, viewsets.ModelViewSet):
    """
    Тут работаем с дисциплинами - создаем, смотрим, редактируем.
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
    lookup_field = 'pk'  # По умолчанию поиск по ID, но get_object поддерживает поиск по названию

    def get_permissions(self):
        # Администратор имеет полные права.
        # Владелец (Teacher) может редактировать/удалять свои дисциплины.
        # Модератор может просматривать все, а редактировать/удалять любые.
        # Остальные пользователи (студенты) могут только просматривать.
        if self.action in ['create']:
            # Создавать могут учителя, администраторы и модераторы
            self.permission_classes = [IsAuthenticated & IsTeacherOrAdminOrModerator]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Обновлять/удалять могут владельцы, администраторы или модераторы
            # Модераторы могут изменять любые объекты, не только свои
            self.permission_classes = [IsAuthenticated & (IsOwnerOrAdminOrModerator | IsModerator)]
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_object(self):
        """
        Получаем дисциплину по ID или по названию.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup = self.kwargs[lookup_url_kwarg]

        # Пробуем найти по ID
        if lookup.isdigit():
            try:
                return Discipline.objects.get(pk=lookup)
            except Discipline.DoesNotExist:
                pass

        # Если не найдено по ID или это не число, ищем по названию
        try:
            obj = Discipline.objects.get(title__iexact=lookup)
            self.check_object_permissions(self.request, obj)
            return obj
        except Discipline.DoesNotExist:
            # Если ничего не найдено, используем стандартный метод
            return super().get_object()



    @extend_schema(
        summary="Получить дисциплину по ID или названию",
        description="Возвращает детали конкретной дисциплины по ID (число) или точному названию (строка).",
        parameters=[
            OpenApiParameter(
                name="pk", type=str, location="path",
                description="ID дисциплины (число) или название дисциплины (строка)"
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
                'Пример создания дисциплины',
                value={'title': 'Математика', 'description': 'Курс по высшей математике'},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Полностью обновить дисциплину",
        description="Полностью обновляет существующую дисциплину по её ID. Доступно только владельцам, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(
                name="pk", type=int, location="path", description="ID дисциплины"
            )
        ],
        examples=[
            OpenApiExample(
                "Пример полного обновления дисциплины",
                value={
                    "title": "Высшая Математика",
                    "description": "Обновленный курс по высшей математике",
                },
                request_only=True,
                media_type="application/json",
            )
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Частично обновить дисциплину",
        description="Частично обновляет существующую дисциплину по её ID. Доступно только владельцам, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(
                name="pk", type=int, location="path", description="ID дисциплины"
            )
        ],
        examples=[
            OpenApiExample(
                "Пример частичного обновления дисциплины",
                value={"description": "Расширенный курс"},
                request_only=True,
                media_type="application/json",
            )
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить дисциплину",
        description="Удаляет дисциплину по её ID. Доступно только владельцам, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(
                name="pk", type=int, location="path", description="ID дисциплины"
            )
        ],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Создает новую дисциплину.
        Автоматически устанавливает текущего пользователя как владельца предмета,
        если это учитель или администратор.
        Если это модератор, владелец не устанавливается.
        """
        user = self.request.user
        if user.groups.filter(name='teacher').exists() or user.is_superuser or user.groups.filter(name='admin').exists():
            serializer.save(owner=user)
        elif user.groups.filter(name='moderator').exists():
            serializer.save(owner=None) # Модераторы создают без привязки к владельцу
        else:
            raise serializers.ValidationError("У вас нет прав для создания дисциплин.")

    def get_queryset(self):
        """
        Возвращает список дисциплин в зависимости от роли пользователя.
        """
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

            # Применяем простую сортировку
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
                queryset = queryset.order_by("display_order", "title")  # По умолчанию по порядку отображения

            return queryset

        return Discipline.objects.none()

    @extend_schema(
        summary="Получить список дисциплин",
        description="Возвращает список всех доступных дисциплин. Все параметры опциональны.",
        parameters=[
            OpenApiParameter(
                name="title",
                type=str,
                location="query",
                description="Поиск по названию дисциплины (опционально)",
                required=False
            ),
            OpenApiParameter(
                name="owner__email",
                type=str,
                location="query",
                description="Поиск по email владельца дисциплины (опционально)",
                required=False
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location="query",
                description="Сортировка. Возможные значения: `title`, `-title`, `created_at`, `-created_at`",
                required=False,
                examples=[
                    OpenApiExample("По названию А-Я", value="title"),
                    OpenApiExample("По названию Я-А", value="-title"),
                    OpenApiExample("Сначала новые", value="-created_at"),
                    OpenApiExample("Сначала старые", value="created_at"),
                ],
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Получить содержимое дисциплины (уроки и тесты)",
        description="Возвращает список уроков и тестов, связанных с указанной дисциплиной.",
        parameters=[
            OpenApiParameter(name='pk', type=int, location='path', description='ID дисциплины')
        ],
        responses={
            200: {
                'description': 'Уроки и тесты дисциплины',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'lessons': {'type': 'array', 'items': LessonSerializer.__name__},
                                'tests': {'type': 'array', 'items': QuizSerializer.__name__}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=True, methods=['get'])
    def get_content(self, request, pk=None):
        """
        Возвращает список уроков и тестов для указанного предмета.
        """
        lessons, tests = get_lessons_and_tests_for_discipline(pk)
        lessons_serializer = LessonSerializer(lessons, many=True, context={'request': request})
        tests_serializer = QuizSerializer(tests, many=True, context={'request': request})
        return Response({
            'lessons': lessons_serializer.data,
            'tests': tests_serializer.data
        }, status=status.HTTP_200_OK)
