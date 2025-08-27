from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Lesson, UserLessonProgress
from .serializers import LessonSerializer, UserLessonProgressSerializer
from Disciplines.common_permissions import IsOwnerOrAdminOrModerator, IsTeacherOrAdminOrModerator
from rest_framework.permissions import IsAuthenticated
from Users.permissions import IsStudent, IsModerator
from utils.cache_mixins import RetrieveCacheMixin
from utils.paginators import StandardResultsSetPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample



@extend_schema(tags=['Уроки'])
class LessonViewSet(RetrieveCacheMixin, viewsets.ModelViewSet):
    """
    Тут работаем с уроками - создаем, смотрим, редактируем.
    """
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "title": ["icontains"],  # Простой поиск по названию
        "discipline__title": ["icontains"],  # Поиск по дисциплине
    }
    lookup_field = 'pk'  # По умолчанию поиск по ID, но get_object поддерживает поиск по названию
    def get_permissions(self):
        if self.action in ['create']:
            # Создавать могут учителя, администраторы и модераторы
            self.permission_classes = [IsAuthenticated & IsTeacherOrAdminOrModerator]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Обновлять/удалять могут владельцы (учителя), администраторы или модераторы
            self.permission_classes = [IsAuthenticated & (IsOwnerOrAdminOrModerator | IsModerator)]
        elif self.action in ['list', 'retrieve']:
            self.permission_classes =  [IsAuthenticated]  # Просматривать могут только аутентифицированные пользователи
        elif self.action in ['update_progress', 'get_progress']:
            self.permission_classes = [IsAuthenticated, IsStudent]  # Только студенты могут обновлять/получать прогресс
        else:
            # Просматривать могут все аутентифицированные пользователи
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_object(self):
        """
        Получаем урок по ID или по названию.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup = self.kwargs[lookup_url_kwarg]

        # Пробуем найти по ID
        if lookup.isdigit():
            try:
                return Lesson.objects.get(pk=lookup)
            except Lesson.DoesNotExist:
                pass

        # Если не найдено по ID или это не число, ищем по названию
        try:
            obj = Lesson.objects.get(title__iexact=lookup)
            self.check_object_permissions(self.request, obj)
            return obj
        except Lesson.DoesNotExist:
            # Если ничего не найдено, используем стандартный метод
            return super().get_object()



    @extend_schema(
        summary="Получить урок по ID или названию",
        description="Возвращает детали конкретного урока по ID (число) или точному названию (строка).",
        parameters=[
            OpenApiParameter(name='pk', type=str, location='path',
                           description='ID урока (число) или название урока (строка)')
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Создать новый урок",
        description="Создает новый урок. Доступно только учителям, администраторам и модераторам.",
        examples=[
            OpenApiExample(
                'Пример создания урока',
                value={'title': 'Введение в Алгебру', 'description': 'Первый урок по алгебре', 'discipline': 1, 'section': 1},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Полностью обновить урок",
        description="Полностью обновляет существующий урок по его ID. Доступно только владельцам, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID урока')
        ],
        examples=[
            OpenApiExample(
                'Пример полного обновления урока',
                value={'title': 'Алгебра для начинающих', 'description': 'Обновленный первый урок по алгебре',
                       'discipline': 1, 'section': 1},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Частично обновить урок",
        description="Частично обновляет существующий урок по его ID. Доступно только владельцам, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID урока')
        ],
        examples=[
            OpenApiExample(
                'Пример частичного обновления урока',
                value={'order': 2},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить урок",
        description="Удаляет урок по его ID. Доступно только владельцам, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID урока')
        ]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        """
        Показываем учителям только их уроки, остальным - все.
        """
        user = self.request.user
        if user.is_authenticated:
            if user.groups.filter(name='teacher').exists() and not (
                    user.is_superuser or user.groups.filter(name='admin').exists()
                    or user.groups.filter(name='moderator').exists()):
                queryset = Lesson.objects.filter(discipline__owner=user) | \
                           Lesson.objects.filter(discipline__owner__isnull=True, owner=user)
            else:
                queryset = Lesson.objects.all()
            # Применяем простую сортировку
            order_by = self.request.query_params.get("order_by", "order")
            if order_by == "title":
                queryset = queryset.order_by("title")
            elif order_by == "-title":
                queryset = queryset.order_by("-title")
            elif order_by == "created_at":
                queryset = queryset.order_by("created_at")
            elif order_by == "-created_at":
                queryset = queryset.order_by("-created_at")
            elif order_by == "order":
                queryset = queryset.order_by("order")
            elif order_by == "-order":
                queryset = queryset.order_by("-order")
            else:
                queryset = queryset.order_by("order", "title")  # По умолчанию по номеру урока

            return queryset
        else:
            return Lesson.objects.none()  # Неаутентифицированные пользователи не видят ничего

    @extend_schema(
        summary="Получить список уроков",
        description="Возвращает список доступных уроков с возможностью поиска и сортировки.",
        parameters=[
            OpenApiParameter(
                name="title",
                type=str,
                location="query",
                description="Поиск по названию урока",
                required=False
            ),
            OpenApiParameter(
                name="discipline__title",
                type=str,
                location="query",
                description="Поиск по названию дисциплины",
                required=False
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location="query",
                description="Сортировка. Возможные значения: `title`, `-title`, `created_at`, `-created_at`, `lesson_order`, `-lesson_order`",
                required=False,
                examples=[
                    OpenApiExample("По названию А-Я", value="title"),
                    OpenApiExample("Сначала новые", value="-created_at"),
                    OpenApiExample("По номеру урока", value="lesson_order"),
                ],
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    def perform_create(self, serializer):
        """
        Создает новый урок.
        Автоматически устанавливает владельца урока при создании.
        Проверяет, что преподаватель создает урок только для своего предмета.
        Модератор может создавать уроки без привязки к себе как владельцу.
        """
        discipline = serializer.validated_data['discipline']
        user = self.request.user

        if user.groups.filter(name='teacher').exists():
            if discipline.owner != user:
                raise serializers.ValidationError("Вы можете создавать уроки только для своих предметов.")
            serializer.save(owner=user)
        elif user.is_superuser or user.groups.filter(name='admin').exists():
            serializer.save(owner=user) # Админ является владельцем, если он создает
        elif user.groups.filter(name='moderator').exists():
            # Модератор может создавать уроки, но они не связаны с ним как владельцем.
            # Владельцем может быть дисциплина.owner или None
            if discipline.owner and discipline.owner != user and not user.is_superuser and not user.groups.filter(name='admin').exists():
                raise serializers.ValidationError("Модератор может создавать уроки только для дисциплин без владельца или своих дисциплин (если он и преподаватель).")
            serializer.save(owner=None) # Урок, созданный модератором, не имеет владельца
        else:
            raise serializers.ValidationError("У вас нет прав для создания уроков.")

    @extend_schema(
        summary="Обновить прогресс урока",
        description="Обновляет прогресс просмотра урока для текущего пользователя (студента). "
                    "Принимает `watched_duration` (сколько секунд просмотрено) и/или `is_completed` (флаг завершения урока).",
        parameters=[
            OpenApiParameter(name='pk', type=int, location='path', description='ID урока'),
        ],
        request={
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'watched_duration': {'type': 'integer', 'description': 'Просмотрено секунд'},
                        'is_completed': {'type': 'boolean', 'description': 'Урок пройден (true/false)'}
                    }
                }
            }
        },
        responses={200: UserLessonProgressSerializer, 404: {'description': 'Прогресс для этого урока не найден.'}}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsStudent])
    def update_progress(self, request):
        """
        Обновляет прогресс просмотра урока для текущего пользователя (студента).
        Принимает `watched_duration` (сколько секунд просмотрено) и/или `is_completed` (флаг завершения урока).
        """
        lesson = self.get_object()
        user = request.user

        # Получаем данные из запроса. Предполагается, что передается 'watched_duration' и/или 'is_completed'
        watched_duration = request.data.get('watched_duration')
        is_completed = request.data.get('is_completed')

        try:
            progress = UserLessonProgress.objects.get(user=user, lesson=lesson)
        except UserLessonProgress.DoesNotExist:
            progress = UserLessonProgress.objects.create(user=user, lesson=lesson)

        if watched_duration is not None:
            # Убеждаемся, что watched_duration не уменьшается и не превышает максимальное время урока (если доступно)
            # Если у урока есть длительность (например, в модели Lesson), можно добавить проверку
            progress.watched_duration = max(progress.watched_duration, int(watched_duration))
            progress.current_time = float(watched_duration)  # Обновляем current_time
            # Если есть общая длительность урока, можно проверять на завершение
            # Допустим, у модели Lesson есть поле `duration_seconds`
            if hasattr(lesson, 'duration_seconds') and lesson.duration_seconds and progress.watched_duration >= lesson.duration_seconds:
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
            OpenApiParameter(name='pk', type=int, location='path', description='ID урока')
        ],
        responses={200: UserLessonProgressSerializer, 404: {'description': 'Прогресс для этого урока не найден.'}}
    )
    @action(detail=True, methods=['get'])
    def get_progress(self, request):
        """
        Получает прогресс просмотра урока для текущего пользователя(студента).
        """
        lesson = self.get_object()
        user = request.user
        try:
            progress = UserLessonProgress.objects.get(user=user, lesson=lesson)
            serializer = UserLessonProgressSerializer(progress)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserLessonProgress.DoesNotExist:
            return Response({"detail": "Прогресс для этого урока не найден."}, status=status.HTTP_404_NOT_FOUND)
