from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Test, Question, Answer, QuizAttempt
from .serializers import (
    QuizSerializer,
    SubmitTestSerializer,
    QuestionSerializer,
    AnswerSerializer,
    QuizAttemptSerializer
)

from Tests.permissions import IsTestOwnerOrAdminOrModerator
from Disciplines.common_permissions import IsTeacherOrAdminOrModerator
from Users.permissions import IsStudent
from utils.cache_mixins import RetrieveCacheMixin
from utils.paginators import StandardResultsSetPagination
from Tests.services import QuizAttemptService
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models

@extend_schema(tags=['Тесты и задания'])
class TestViewSet(RetrieveCacheMixin, viewsets.ModelViewSet):
    """
    Тут работаем с тестами - создаем, смотрим, проходим.
    """
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "title": ["icontains"],  # Простой поиск по названию
        "discipline__title": ["icontains"],  # Поиск по дисциплине
    }

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.groups.filter(name="teacher").exists() and not (
                user.is_superuser
                or user.groups.filter(name="admin").exists()
                or user.groups.filter(name="moderator").exists()
            ):
                queryset = Test.objects.filter(owner=user)
            elif (
                user.is_superuser
                or user.groups.filter(name="admin").exists()
                or user.groups.filter(name="moderator").exists()
            ):
                queryset = Test.objects.all()
            elif user.groups.filter(name="student").exists():
                # Для студентов - показываем только тесты для купленного контента
                from Payments.models import PurchasedContent

                # Получаем купленные дисциплины и уроки
                purchased_disciplines = PurchasedContent.objects.filter(
                    user=user, discipline__isnull=False
                ).values_list('discipline_id', flat=True)

                purchased_lessons = PurchasedContent.objects.filter(
                    user=user, lesson__isnull=False
                ).values_list('lesson_id', flat=True)

                # Фильтруем тесты: либо принадлежат купленной дисциплине, либо купленному уроку
                queryset = Test.objects.filter(
                    models.Q(discipline_id__in=purchased_disciplines) |
                    models.Q(lesson_id__in=purchased_lessons)
                )
            else:
                queryset = Test.objects.none()  # Пользователи без роли не видят ничего

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
                queryset = queryset.order_by("title")  # По умолчанию

            return queryset
        else:
            # Для неаутентифицированных пользователей возвращаем пустой queryset
            return Test.objects.none()

    @extend_schema(
        summary="Получить список тестов",
        description="Возвращает список доступных тестов с возможностью поиска и сортировки.",
        parameters=[
            OpenApiParameter(
                name="title",
                type=str,
                location="query",
                description="Поиск по названию теста",
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
                description="Сортировка. Возможные значения: `title`, `-title`, `created_at`, `-created_at`",
                required=False,
                examples=[
                    OpenApiExample("По названию А-Я", value="title"),
                    OpenApiExample("Сначала новые", value="-created_at"),
                ],
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Получить тест по ID",
        description="Возвращает детали конкретного теста по его уникальному идентификатору. Доступно только для аутентифицированных пользователей.",
        parameters=[
            OpenApiParameter(
                name="id", type=int, location="path", description="ID теста"
            )
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Создать новый тест",
        description="Создает новый тест. Доступно только учителям, администраторам и модераторам.",
        examples=[
            OpenApiExample(
                'Пример создания теста',
                value={'title': 'Тест по Алгебре', 'description': 'Проверочный тест по основам алгебры', 'discipline': 'Алгебра'},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Полностью обновить тест",
        description="Полностью обновляет существующий тест по его ID. Доступно только владельцам, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID теста')
        ],
        examples=[
            OpenApiExample(
                'Пример полного обновления теста',
                value={'title': 'Обновленный тест по Алгебре', 'description': 'Расширенный проверочный тест'},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Частично обновить тест",
        description="Частично обновляет существующий тест по его ID. Доступно только владельцам, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID теста')
        ],
        examples=[
            OpenApiExample(
                'Пример частичного обновления теста',
                value={'description': 'Тест для продвинутых'},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить тест",
        description="Удаляет тест по его ID. Доступно только владельцам, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID теста')
        ]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Создаем тест и назначаем владельца.
        """
        user = self.request.user
        if user.groups.filter(name='teacher').exists() or user.is_superuser or user.groups.filter(name='admin').exists():
            serializer.save(owner=user)
        elif user.groups.filter(name='moderator').exists():
            serializer.save(owner=None) # Модераторы создают без привязки к владельцу
        else:
            raise serializers.ValidationError("У вас нет прав для создания тестов.")

    @extend_schema(
        summary="Пройти тест",
        description="Принимает ответы пользователя на тест и подсчитывает результат. Доступно только студентам.",
        request=SubmitTestSerializer,
        responses={
            200: QuizSerializer,
            400: {'description': 'Ошибка валидации или активная попытка не найдена.'},
            404: {'description': 'Вопрос или ответ не найдены.'}
        }
    )
    @action(detail=True, methods=['post'])
    def submit_test(self, request):
        """
        Принимает ответы пользователя на тест и подсчитывает результат.
        Доступно только студентам.
        """
        quiz = self.get_object()
        user = request.user

        # Проверяем, что есть активная попытка
        try:
            attempt = QuizAttempt.objects.get(user=user, quiz=quiz, is_completed=False)
        except QuizAttempt.DoesNotExist:
            return Response({"detail": "Активная попытка прохождения теста не найдена. Начните тест сначала."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = SubmitTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_answers_data = serializer.validated_data['answers']

        # Вызываем сервис для обработки отправки теста и подсчета баллов
        try:
            QuizAttemptService.submit_test_attempt(attempt, user_answers_data)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        serializer = QuizSerializer(quiz, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Начать новую попытку прохождения теста",
        description="Создает новую запись попытки прохождения теста для текущего пользователя. "
                    "Если есть незавершенные попытки для этого теста, они будут помечены как завершенные и будет создана новая.",
        responses={201: QuizAttemptSerializer}
    )
    @action(detail=True, methods=['post'])
    def start_test(self, request):
        quiz = self.get_object()
        user = request.user

        # Помечаем все предыдущие незавершенные попытки как завершенные (но без подсчета баллов, если они не были отправлены)
        QuizAttempt.objects.filter(user=user, quiz=quiz, is_completed=False).update(is_completed=True,
                                                                                    end_time=timezone.now())

        attempt = QuizAttempt.objects.create(user=user, quiz=quiz, start_time=timezone.now())
        serializer = QuizAttemptSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Получить текущую активную попытку прохождения теста",
        description="Возвращает детали текущей активной (незавершенной) попытки прохождения теста для пользователя.",
        responses={200: QuizAttemptSerializer, 404: {'description': 'Активная попытка не найдена.'}}
    )
    @action(detail=True, methods=['get'])
    def get_current_attempt(self, request):
        quiz = self.get_object()
        user = request.user
        try:
            attempt = QuizAttempt.objects.get(user=user, quiz=quiz, is_completed=False)
            serializer = QuizAttemptSerializer(attempt)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except QuizAttempt.DoesNotExist:
            return Response({"detail": "Активная попытка прохождения теста не найдена."},
                            status=status.HTTP_404_NOT_FOUND)


@extend_schema(tags=["Вопросы"])
class QuestionViewSet(viewsets.ModelViewSet):
    """
    Тут работаем с вопросами к тестам.
    """
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [AllowAny]
    def get_permissions(self):
        # Применяем IsTestOwnerOrAdminOrModerator для всех модифицирующих операций
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsTestOwnerOrAdminOrModerator]
        else:
            self.permission_classes = [AllowAny]
        return super().get_permissions()

    @extend_schema(
        summary="Получить список вопросов",
        description="Возвращает список всех вопросов. Доступно для всех пользователей."
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Получить вопрос по ID",
        description="Возвращает детали конкретного вопроса по его уникальному идентификатору.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID вопроса')
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Создать новый вопрос",
        description="Создает новый вопрос для теста. Доступно только владельцам теста, администраторам и модераторам.",
        examples=[
            OpenApiExample(
                'Пример создания вопроса',
                value={'test': 1, 'text': 'Какой язык программирования является основным для Django?', 'order': 1,
                       'is_multiple': False,
                       'answers': [{'text': 'Python', 'is_correct': True}, {'text': 'Java', 'is_correct': False}]},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Полностью обновить вопрос",
        description="Полностью обновляет существующий вопрос по его ID. Доступно только владельцам теста, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID вопроса')
        ],
        examples=[
            OpenApiExample(
                'Пример полного обновления вопроса',
                value={'test': 1, 'text': 'Обновленный вопрос', 'order': 1, 'is_multiple': False,
                       'answers': [{'text': 'Ответ 1', 'is_correct': True}, {'text': 'Ответ 2', 'is_correct': False}]},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Частично обновить вопрос",
        description="Частично обновляет существующий вопрос по его ID. Доступно только владельцам теста, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID вопроса')
        ],
        examples=[
            OpenApiExample(
                'Пример частичного обновления вопроса',
                value={'text': 'Частично обновленный вопрос'},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить вопрос",
        description="Удаляет вопрос по его ID. Доступно только владельцам теста, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID вопроса')
        ]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


@extend_schema(tags=["Ответы"])
class AnswerViewSet(viewsets.ModelViewSet):
    """
    Тут работаем с ответами к вопросам.
    """
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        # Применяем IsTestOwnerOrAdminOrModerator для всех модифицирующих операций
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsTestOwnerOrAdminOrModerator]
        else:
            self.permission_classes = [AllowAny]
        return super().get_permissions()

    @extend_schema(
        summary="Получить список ответов",
        description="Возвращает список всех ответов. Доступно для всех пользователей."
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Получить ответ по ID",
        description="Возвращает детали конкретного ответа по его уникальному идентификатору.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID ответа')
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Создать новый ответ",
        description="Создает новый ответ для вопроса. Доступно только владельцам теста, администраторам и модераторам.",
        examples=[
            OpenApiExample(
                'Пример создания ответа',
                value={'question': 1, 'text': 'Python', 'is_correct': True},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Полностью обновить ответ",
        description="Полностью обновляет существующий ответ по его ID. Доступно только владельцам теста, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID ответа')
        ],
        examples=[
            OpenApiExample(
                'Пример полного обновления ответа',
                value={'question': 1, 'text': 'Обновленный ответ', 'is_correct': False},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Частично обновить ответ",
        description="Частично обновляет существующий ответ по его ID. Доступно только владельцам теста, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID ответа')
        ],
        examples=[
            OpenApiExample(
                'Пример частичного обновления ответа',
                value={'is_correct': True},
                request_only=True,
                media_type='application/json',
            )
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить ответ",
        description="Удаляет ответ по его ID. Доступно только владельцам теста, администраторам и модераторам.",
        parameters=[
            OpenApiParameter(name='id', type=int, location='path', description='ID ответа')
        ]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
