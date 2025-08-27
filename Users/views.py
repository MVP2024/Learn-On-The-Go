import secrets

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action

import logging

logger = logging.getLogger(__name__)

from .serializers import RegisterSerializer, UserProfilePublicSerializer, \
    UserProfilePrivateSerializer, RequestAdminKeySerializer, AdminKeyLoginSerializer

from .permissions import IsOwnerOrReadOnly
from .models import User
from Admin.models import AdminKey
from .tasks import send_admin_key_email, notify_superusers_about_admin_key_request
from rest_framework_simplejwt.tokens import RefreshToken


@extend_schema(tags=["Регистрация нового пользователя"])
class RegisterView(generics.CreateAPIView):
    """
    API View для регистрации новых пользователей.
    Доступен для неавторизованных пользователей.
    """

    serializer_class = RegisterSerializer
    permission_classes = [
        AllowAny
    ]  # Разрешаем доступ для неавторизованных пользователей

    @extend_schema(
        summary="Зарегистрировать нового пользователя",
        description="Создает новую учетную запись пользователя с указанной ролью (студент, преподаватель, администратор). "
        "Для регистрации администратора/модератора аккаунт будет создан, но потребует активации суперпользователем для получения ключа.",
        examples=[
            OpenApiExample(
                "Пример регистрации студента",
                value={
                    "email": "student@example.com",
                    "password": "password123",
                    "role": "student",
                    "first_name": "Иван",
                    "last_name": "Иванов",
                },
                request_only=True,
                media_type="application/json",
            ),
            OpenApiExample(
                "Пример регистрации преподавателя",
                value={
                    "email": "teacher@example.com",
                    "password": "password123",
                    "role": "teacher",
                    "first_name": "Петр",
                    "last_name": "Петров",
                },
                request_only=True,
                media_type="application/json",
            ),
            OpenApiExample(
                "Пример регистрации администратора",
                value={
                    "email": "admin@example.com",
                    "password": "password123",
                    "role": "admin",
                    "first_name": "Анна",
                    "last_name": "Смирнова",
                },
                request_only=True,
                media_type="application/json",
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=["Профили пользователей"])
class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet для просмотра и редактирования профилей пользователей.
    Авторизованный пользователь может просматривать любой профиль,
    но редактировать только свой.
    """

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "email": ["exact", "icontains"],
        "first_name": ["exact", "icontains"],
        "last_name": ["exact", "icontains"],
        "role": ["exact"],
        "is_active": ["exact"],
    }
    lookup_field = "email"
    lookup_url_kwarg = "email"

    def get_serializer_class(self):
        if self.action == "me":
            return UserProfilePrivateSerializer
        if self.action == "request_admin_key":
            return RequestAdminKeySerializer
        if self.action == "admin_key_login":
            return AdminKeyLoginSerializer

        # Для действия 'list' всегда используем публичный сериализатор
        if self.action == "list":
            return UserProfilePublicSerializer
        # Для детальных действий (retrieve, update, partial_update, destroy)
        # Если пользователь аутентифицирован и является владельцем профиля, используем приватный сериализатор.
        # В противном случае используем публичный сериализатор.
        if self.request.user.is_authenticated:
            try:
                obj = self.get_object()
                if (
                    obj == self.request.user
                ):  # Проверяем, является ли полученный объект текущим пользователем
                    return UserProfilePrivateSerializer
            except Exception:
                # Во время генерации схемы, или если get_object не удается по какой-либо причине (например, неверный PK),
                # мы корректно возвращаемся к публичному сериализатору.
                pass  # Переходим к возврату UserProfilePublicSerializer

        # По умолчанию для не-владельцев, неаутентифицированных пользователей или во время генерации схемы
        return UserProfilePublicSerializer

    def retrieve(self, request, *args, **kwargs):
        # Этот метод предназначен для получения одного объекта
        return super().retrieve(request, *args, **kwargs)

    def get_permissions(self):
        """
        Устанавливает права доступа для различных действий.
        'me' - только авторизованный пользователь.
        'retrieve' (просмотр другого профиля) - любой авторизованный.
        'update', 'partial_update' - только владелец.
        'generate_new_admin_key' - только суперпользователь.
        'request_admin_key' - только аутентифицированные пользователи с ролью admin/moderator, которые еще не активировали свой ключ.
        'admin_key_login' - AllowAny, так как это специальный логин
        """
        if self.action == "me":
            self.permission_classes = [IsAuthenticated]
        elif self.action in ["update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        elif self.action == "generate_new_admin_key":
            # Проверка на is_superuser внутри метода generate_new_admin_key
            self.permission_classes = [IsAuthenticated]
        elif self.action == "request_admin_key":
            # Пользователь должен быть аутентифицирован и иметь роль admin/moderator
            # Дополнительная проверка на необходимость ключа будет в самом методе
            self.permission_classes = [IsAuthenticated]
        elif self.action == "admin_key_login":
            self.permission_classes = [AllowAny]
        elif self.action == "list":
            self.permission_classes = [IsAuthenticated]
        elif self.action == "retrieve":
            self.permission_classes = [IsAuthenticated]
        else:  # list, retrieve
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    @extend_schema(
        summary="Получить список профилей пользователей",
        description="Возвращает список всех профилей пользователей. Доступно только аутентифицированным пользователям.",
        parameters=[
            OpenApiParameter(
                name="order_by",
                type=str,
                location="query",
                description="Поле для сортировки. Возможные значения: `email_asc`, `email_desc`, `first_name_asc`, `first_name_desc`, `last_name_asc`, `last_name_desc`, `role_asc`, `role_desc`.",
                examples=[
                    OpenApiExample("По email (по возрастанию)", value="email_asc"),
                    OpenApiExample("По фамилии (по убыванию)", value="last_name_desc"),
                ],
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        # Добавляем сортировку в get_queryset, так как list сам по себе не обрабатывает order_by
        queryset = self.filter_queryset(self.get_queryset())

        order_by = self.request.query_params.get("order_by")
        if order_by == "email_asc":
            queryset = queryset.order_by("email")
        elif order_by == "email_desc":
            queryset = queryset.order_by("-email")
        elif order_by == "first_name_asc":
            queryset = queryset.order_by("first_name")
        elif order_by == "first_name_desc":
            queryset = queryset.order_by("-first_name")
        elif order_by == "last_name_asc":
            queryset = queryset.order_by("last_name")
        elif order_by == "last_name_desc":
            queryset = queryset.order_by("-last_name")
        elif order_by == "role_asc":
            queryset = queryset.order_by("role")
        elif order_by == "role_desc":
            queryset = queryset.order_by("-role")
        else:
            queryset = queryset.order_by("email")  # Сортировка по умолчанию

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Получить профиль пользователя по ID или Email",
        description="Возвращает детали конкретного профиля пользователя по его ID или Email. Доступно только аутентифицированным пользователям.",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location="path",
                description="ID пользователя (используется по умолчанию, если не указан email)",
            ),
            OpenApiParameter(
                name="email",
                type=str,
                location="path",
                description="Email пользователя (может использоваться вместо ID)",
            ),
            OpenApiParameter(
                name="last_name",
                type=str,
                location="query",
                description="Фамилия пользователя (для фильтрации списка, не для прямого получения)",
            ),
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        if (
            "last_name" in request.query_params
        ):  # Если пытаются получить по фамилии через retrieve, перенаправляем на list
            return Response(
                {
                    "detail": "Получение профиля по фамилии возможно только через фильтрацию списка пользователей. Используйте /profiles/?last_name=...",
                    "data": self.list(request).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )  # Изменено
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Полностью обновить собственный профиль",
        description="Полностью обновляет собственный профиль пользователя. Доступно только владельцу профиля. Email изменить нельзя.",
        parameters=[
            OpenApiParameter(
                name="id", type=int, location="path", description="ID пользователя"
            )
        ],
        examples=[
            OpenApiExample(
                "Пример полного обновления профиля",
                value={
                    "first_name": "Иван",
                    "last_name": "Иванов",
                    "phone_number": "+79991234567",
                },
                request_only=True,
                media_type="application/json",
            )
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Частично обновить собственный профиль",
        description="Частично обновляет собственный профиль пользователя. Доступно только владельцу профиля. Email изменить нельзя.",
        parameters=[
            OpenApiParameter(
                name="id", type=int, location="path", description="ID пользователя"
            )
        ],
        examples=[
            OpenApiExample(
                "Пример частичного обновления профиля",
                value={"first_name": "Новое Имя"},
                request_only=True,
                media_type="application/json",
            )
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить собственный профиль",
        description="Удаляет собственный профиль пользователя. Доступно только владельцу профиля.",
        parameters=[
            OpenApiParameter(
                name="id", type=int, location="path", description="ID пользователя"
            )
        ],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Получить профиль текущего пользователя",
        description="Возвращает профиль текущего аутентифицированного пользователя.",
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Возвращает профиль текущего пользователя.
        Доступно только аутентифицированным пользователям.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary="Сгенерировать и отправить новый админ-ключ",
        description="Только суперпользователь может сгенерировать новый уникальный административный ключ "
        "для указанного пользователя (если его роль - администратор или модератор) и отправить его по email. "
        "Старый ключ будет деактивирован, а пользователь будет активирован, если он неактивен.",
        request=RequestAdminKeySerializer,
        responses={
            200: {
                "description": "Новый админ-ключ успешно сгенерирован и отправлен пользователю."
            },
            400: {
                "description": "Ошибка: пользователь не является администратором/модератором или неверный email."
            },
            403: {
                "description": "Недостаточно прав для выполнения операции (только суперпользователь)."
            },
            404: {"description": "Пользователь не найден."},
        },
    )
    @action(detail=False, methods=["post"])
    def generate_new_admin_key(self, request):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Только суперпользователь может генерировать админ-ключи."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RequestAdminKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Пользователь с таким email не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            # Деактивируем все предыдущие активные ключи для этого пользователя
            AdminKey.objects.filter(user=user, is_active=True).update(is_active=False)

            # Генерируем новый ключ
            new_key_value = secrets.token_urlsafe(32)
            AdminKey.objects.create(
                user=user, key=new_key_value, is_active=True, email=user.email
            )  # Сохраняем email для наглядности

            # Активируем пользователя, если он неактивен, и устанавливаем флаг is_admin_key_required
            if not user.is_active or not user.is_admin_key_required:
                user.is_active = True
                user.is_admin_key_required = True
                user.save()

            # Отправляем новый ключ пользователю по email
            send_admin_key_email.delay(user.email, new_key_value, user.role)

        return Response(
            {
                "detail": f"Новый админ-ключ успешно сгенерирован и отправлен на {user.email}."
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Запросить админ-ключ (для администраторов/модераторов)",
        description="Пользователь с ролью 'администратор' или 'модератор', который еще не имеет активного админ-ключа "
        "или не активировал свой аккаунт, может запросить отправку нового ключа на свой email. "
        "Запрос может быть обработан только суперпользователем.",
        request=RequestAdminKeySerializer,
        responses={
            200: {
                "description": "Запрос на получение админ-ключа отправлен. Ключ будет отправлен на указанный email после одобрения суперпользователем."
            },
            400: {
                "description": "Ошибка: неверная роль пользователя или ключ уже выдан."
            },
            404: {"description": "Пользователь не найден."},
        },
    )
    @action(
        detail=False, methods=["post"], permission_classes=[AllowAny]
    )  # AllowAny чтобы даже неактивный пользователь мог запросить
    def request_admin_key(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Пользователь с таким email не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.role not in ["admin", "moderator"]:
            return Response(
                {
                    "detail": "Запрос админ-ключа доступен только для пользователей с ролями администратор или модератор."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверяем, есть ли активный ключ или уже был выполнен первый вход
        if user.has_logged_in_with_key:
            return Response(
                {
                    "detail": "Вы уже вошли с админ-ключом. Дополнительный ключ не требуется."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Отправляем уведомление суперпользователю о новой заявке через Celery
        notify_superusers_about_admin_key_request.delay(user.email, user.role)

        return Response(
            {
                "detail": "Запрос на получение админ-ключа отправлен. Ключ будет отправлен на ваш email после одобрения суперпользователем."
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Вход для администраторов/модераторов с админ-ключом",
        description="Используется администраторами и модераторами для первого входа с использованием выданного админ-ключа. После успешного входа ключ деактивируется.",
        request=AdminKeyLoginSerializer,
        responses={
            200: {
                "description": "Успешный вход. Возвращает токены доступа.",
                "content": {
                    "application/json": {
                        "example": {"access": "eyJ...", "refresh": "eyJ..."}
                    }
                },
            },
            400: {"description": "Неверные учетные данные или админ-ключ."},
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def admin_key_login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = (
            serializer.user
        )  # Получаем пользователя из валидации AdminKeyLoginSerializer

        logger.info(f"Admin key login successful for user: {user.email} (role: {user.role})")

        # Генерируем JWT токены для пользователя
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )
