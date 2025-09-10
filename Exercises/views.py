from django.utils import timezone
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

from Exercises.permissions import IsTestOwnerOrAdminOrModerator
from Exercises.services import QuizAttemptService, _accessible_tests_for_student
from utils.cache_mixins import RetrieveCacheMixin
from utils.common_mixins import OwnerCreateMixin, TitleOrPkLookupMixin
from utils.paginators import StandardResultsSetPagination

from .models import Answer, Question, QuizAttempt, Test
from .serializers import (
    AnswerSerializer,
    QuestionSerializer,
    QuizAttemptSerializer,
    QuizSerializer,
    SubmitTestSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="Список тестов",
        description="Возвращает список тестов с фильтрацией и пагинацией.",
        parameters=[
            OpenApiParameter(
                name="title__icontains",
                type=str,
                location="query",
                description="Поиск по названию теста (частичное совпадение)",
            ),
            OpenApiParameter(
                name="discipline__title__icontains",
                type=str,
                location="query",
                description="Поиск по названию дисциплины (частичное совпадение)",
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
    ),
    retrieve=extend_schema(
        summary="Детали теста",
        description="Возвращает подробную информацию о тесте, включая вопросы.",
    ),
    create=extend_schema(
        summary="Создать тест",
        description="Создаёт новый тест (доступно учителям/админам/модераторам).",
        request=QuizSerializer,
        responses={201: QuizSerializer},
        examples=[
            OpenApiExample(
                "Пример создания теста",
                value={
                    "title": "Контрольная по главе 1",
                    "description": "Тест на знание материала главы 1",
                    "discipline": "matematika-slug",
                    "lesson": None,
                    "section": None,
                },
                request_only=True,
                media_type="application/json",
            )
        ],
    ),
    update=extend_schema(
        summary="Обновить тест", description="Полное обновление теста."
    ),
    partial_update=extend_schema(
        summary="Частичное обновление теста",
        description="Частичное обновление полей теста.",
    ),
    destroy=extend_schema(
        summary="Удалить тест",
        description="Удаляет тест (только владельцу/модератору/админу).",
    ),
)
@extend_schema(tags=["Тесты и задания"])
class TestViewSet(
    OwnerCreateMixin, TitleOrPkLookupMixin, RetrieveCacheMixin, viewsets.ModelViewSet
):
    """
    Тут работаем с тестами - создаем, смотрим, проходим.
    """

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "title": ["icontains"],
        "discipline__title": ["icontains"],
    }
    lookup_field = "pk"
    lookup_value_regex = r"[^/]+"

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
                queryset = _accessible_tests_for_student(user)
            else:
                queryset = Test.objects.none()
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
                queryset = queryset.order_by("title")
            return queryset
        else:
            return Test.objects.none()

    @extend_schema(
        summary="Поиск тестов по названию",
        description=(
            "Поиск тестов по точному названию (case-insensitive) или частичному совпадению (icontains) при exact=false."
        ),
        parameters=[
            OpenApiParameter(
                name="title",
                type=str,
                location="query",
                description="Название теста",
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
        responses={200: QuizSerializer(many=True)},
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

    def retrieve(self, request, *args, **kwargs):
        """
        Получаем тест по pk или по названию (и по slug-ссылке, если у теста есть поле slug).
         Отличаем ошибку 404 (не существует) от ошибки 403 (студент существует, но у него нет доступа).
        """
        lookup_url_kwarg = getattr(self, "lookup_url_kwarg", None) or self.lookup_field
        lookup = kwargs.get(lookup_url_kwarg)
        if lookup is None and lookup_url_kwarg != "id":
            lookup = kwargs.get("id")

        if lookup is None:
            return super().retrieve(request, *args, **kwargs)

        try:
            lookup_str = str(lookup)
        except Exception:
            return super().retrieve(request, *args, **kwargs)

        quiz = None

        # пробуем использовать slug (если поле существует), а затем title__iexact
        if not lookup_str.isdigit():
            try:
                Test._meta.get_field("slug")
                has_slug = True
            except Exception:
                has_slug = False

            if has_slug:
                try:
                    quiz = Test.objects.get(slug=lookup_str)
                except Test.DoesNotExist:
                    quiz = None

            if quiz is None:
                matches = Test.objects.filter(title__iexact=lookup_str)
                count = matches.count()
                if count == 1:
                    quiz = matches.first()
                elif count > 1:
                    id_param = request.query_params.get(
                        "id"
                    ) or request.query_params.get("pk")
                    if id_param:
                        try:
                            pk_val = int(id_param)
                        except Exception:
                            return Response(
                                {"detail": "Параметр id должен быть числом (pk)."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                        try:
                            quiz = matches.get(pk=pk_val)
                        except matches.model.DoesNotExist:
                            return Response(
                                {
                                    "detail": f"Объект с id={pk_val} и title='{lookup_str}' не найден среди совпадений."
                                },
                                status=status.HTTP_404_NOT_FOUND,
                            )
                    else:
                        # Если найдено несколько результатов и пользователь не указал точно с помощью ?id=,
                        # вернём 404, чтобы пользователь, ожидавший поиска по первичному ключу,
                        # получил сообщение «Не найдено».
                        return Response(
                            {
                                "detail": "Несколько объектов с таким названием найдено; укажите id в параметрах"
                                " запроса или используйте числовой PK в пути."
                            },
                            status=status.HTTP_404_NOT_FOUND,
                        )

        # numeric lookup -> try pk
        if quiz is None and lookup_str.isdigit():
            try:
                quiz = Test.objects.get(pk=int(lookup_str))
            except Test.DoesNotExist:
                return Response(
                    {"detail": "Тест не найден."}, status=status.HTTP_404_NOT_FOUND
                )

        if quiz is None:
            return super().retrieve(request, *args, **kwargs)

        user = request.user
        # для учащихся: проверяем доступность, но разрешаем доступ, если у учащегося уже есть активная попытка
        if user.groups.filter(name="student").exists():
            accessible = _accessible_tests_for_student(user).filter(pk=quiz.pk).exists()
            if not accessible and not (
                user.is_superuser
                or user.groups.filter(name__in=["admin", "moderator"]).exists()
            ):
                has_active_attempt = QuizAttempt.objects.filter(
                    user=user, quiz=quiz, is_completed=False
                ).exists()
                if not has_active_attempt:
                    return Response(
                        {
                            "detail": "Доступ к этому тесту закрыт. Пройдите соответствующий урок или дисциплину."
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

        self.check_object_permissions(request, quiz)
        serializer = self.get_serializer(quiz, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        user = request.user
        if not (
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.groups.filter(name__in=["admin", "moderator"]).exists()
                or user.groups.filter(name="teacher").exists()
            )
        ):
            return Response(
                {"detail": "У вас нет разрешения на выполнение этого действия."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsTestOwnerOrAdminOrModerator]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    @extend_schema(
        summary="Пройти тест",
        description="Принимает ответы пользователя на тест и подсчитывает результат. Доступно только студентам.",
        request=SubmitTestSerializer,
        responses={
            200: QuizSerializer,
            400: {"description": "Ошибка валидации или активная попытка не найдена."},
            404: {"description": "Вопрос или ответ не найдены."},
        },
    )
    @action(detail=True, methods=["post"])
    def submit_test(self, request, pk=None):
        user = request.user
        try:
            quiz = Test.objects.get(pk=pk)
        except Test.DoesNotExist:
            return Response(
                {"detail": "Тест не найден."}, status=status.HTTP_404_NOT_FOUND
            )

        # Если у учащегося есть активная попытка, разрешите продолжить отправку формы
        attempt = QuizAttempt.objects.filter(
            user=user, quiz=quiz, is_completed=False
        ).first()

        # Если активной попытки не было, выполняем проверку доступа для учащихся
        if attempt is None and user.groups.filter(name="student").exists():
            accessible = _accessible_tests_for_student(user).filter(pk=pk).exists()
            if not accessible and not (
                user.is_superuser
                or user.groups.filter(name__in=["admin", "moderator"]).exists()
            ):
                return Response(
                    {
                        "detail": "Доступ к этому тесту закрыт. Пройдите соответствующий урок или дисциплину."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # obj разрешения
        self.check_object_permissions(request, quiz)

        if attempt is None:
            return Response(
                {
                    "detail": "Активная попытка прохождения теста не найдена. Начните тест сначала."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubmitTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_answers_data = serializer.validated_data["answers"]
        try:
            QuizAttemptService.submit_test_attempt(attempt, user_answers_data)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        out_ser = QuizSerializer(quiz, context={"request": request})
        return Response(out_ser.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Начать новую попытку прохождения теста",
        description="Создает новую запись попытки прохождения теста для текущего пользователя.",
        responses={201: QuizAttemptSerializer},
    )
    @action(detail=True, methods=["post"])
    def start_test(self, request, pk=None):
        user = request.user
        try:
            quiz = Test.objects.get(pk=pk)
        except Test.DoesNotExist:
            return Response(
                {"detail": "Тест не найден."}, status=status.HTTP_404_NOT_FOUND
            )

        if user.groups.filter(name="student").exists():
            accessible = _accessible_tests_for_student(user).filter(pk=pk).exists()
            if not accessible and not (
                user.is_superuser
                or user.groups.filter(name__in=["admin", "moderator"]).exists()
            ):
                return Response(
                    {
                        "detail": "Доступ к этому тесту закрыт. Пройдите соответствующий урок или дисциплину."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        self.check_object_permissions(request, quiz)

        QuizAttempt.objects.filter(user=user, quiz=quiz, is_completed=False).update(
            is_completed=True, end_time=timezone.now()
        )
        attempt = QuizAttempt.objects.create(
            user=user, quiz=quiz, start_time=timezone.now()
        )
        serializer = QuizAttemptSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Получить текущую активную попытку прохождения теста",
        description="Возвращает детали текущей активной (незавершенной) попытки прохождения теста для пользователя.",
        responses={
            200: QuizAttemptSerializer,
            404: {"description": "Активная попытка не найдена."},
        },
    )
    @action(detail=True, methods=["get"])
    def get_current_attempt(self, request, pk=None):
        user = request.user
        try:
            quiz = Test.objects.get(pk=pk)
        except Test.DoesNotExist:
            return Response(
                {"detail": "Тест не найден."}, status=status.HTTP_404_NOT_FOUND
            )

        # Если у пользователя есть активная попытка возврата, она возвращена независимо от проверки доступа
        attempt = QuizAttempt.objects.filter(
            user=user, quiz=quiz, is_completed=False
        ).first()
        if attempt:
            serializer = QuizAttemptSerializer(attempt)
            return Response(serializer.data, status=status.HTTP_200_OK)

        if user.groups.filter(name="student").exists():
            accessible = _accessible_tests_for_student(user).filter(pk=pk).exists()
            if not accessible and not (
                user.is_superuser
                or user.groups.filter(name__in=["admin", "moderator"]).exists()
            ):
                return Response(
                    {
                        "detail": "Доступ к этому тесту закрыт. Пройдите соответствующий урок или дисциплину."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        self.check_object_permissions(request, quiz)

        attempt = QuizAttempt.objects.filter(
            user=user, quiz=quiz, is_completed=False
        ).first()
        if attempt:
            serializer = QuizAttemptSerializer(attempt)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"detail": "Активная попытка прохождения теста не найдена."},
            status=status.HTTP_404_NOT_FOUND,
        )


@extend_schema_view(
    list=extend_schema(
        summary="Список вопросов", description="Возвращает список вопросов."
    ),
    retrieve=extend_schema(
        summary="Детали вопроса", description="Возвращает детали вопроса и его ответы."
    ),
    create=extend_schema(
        summary="Создать вопрос",
        description="Создает новый вопрос (только владелец/модератор/админ).",
        request=QuestionSerializer,
        responses={201: QuestionSerializer},
        examples=[
            OpenApiExample(
                "Пример создания вопроса",
                value={
                    "test": 1,
                    "text": "Что такое 2+2?",
                    "question_order": 1,
                    "is_multiple": False,
                },
                request_only=True,
                media_type="application/json",
            )
        ],
    ),
    update=extend_schema(
        summary="Обновить вопрос", description="Полное обновление вопроса."
    ),
    partial_update=extend_schema(
        summary="Частично обновить вопрос", description="Частичное обновление вопроса."
    ),
    destroy=extend_schema(summary="Удалить вопрос", description="Удаляет вопрос."),
)
@extend_schema(tags=["Вопросы"])
class QuestionViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if (
                user.is_superuser
                or user.groups.filter(name__in=["admin", "moderator"]).exists()
                or user.groups.filter(name="teacher").exists()
            ):
                return Question.objects.all()
            if user.groups.filter(name="student").exists():
                accessible_tests = _accessible_tests_for_student(user)
                return Question.objects.filter(test__in=accessible_tests)
        return Question.objects.none()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsTestOwnerOrAdminOrModerator]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema_view(
    list=extend_schema(
        summary="Список ответов", description="Возвращает ответы для вопросов."
    ),
    retrieve=extend_schema(
        summary="Детали ответа", description="Возвращает подробности ответа."
    ),
    create=extend_schema(
        summary="Создать ответ",
        description="Создаёт ответ (только владелец теста/модератор/админ).",
        request=AnswerSerializer,
        responses={201: AnswerSerializer},
        examples=[
            OpenApiExample(
                "Пример создания ответа",
                value={
                    "question": 1,
                    "text": "4",
                    "is_correct": True,
                },
                request_only=True,
                media_type="application/json",
            )
        ],
    ),
    update=extend_schema(
        summary="Обновить ответ", description="Полное обновление ответа."
    ),
    partial_update=extend_schema(
        summary="Частично обновить ответ", description="Частичное обновление ответа."
    ),
    destroy=extend_schema(summary="Удалить ответ", description="Удаляет ответ."),
)
@extend_schema(tags=["Ответы"])
class AnswerViewSet(viewsets.ModelViewSet):
    serializer_class = AnswerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if (
                user.is_superuser
                or user.groups.filter(name__in=["admin", "moderator"]).exists()
                or user.groups.filter(name="teacher").exists()
            ):
                return Answer.objects.all()
            if user.groups.filter(name="student").exists():
                accessible_tests = _accessible_tests_for_student(user)
                return Answer.objects.filter(question__test__in=accessible_tests)
        return Answer.objects.none()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsTestOwnerOrAdminOrModerator]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
