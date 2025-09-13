import logging
import secrets

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from Admin.models import AdminKey
from Users.models import User
from Users.permissions import IsOwnerOrReadOnly
from Users.serializers import (
    AdminKeyLoginSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    RequestAdminKeySerializer,
    UserProfilePrivateSerializer,
    UserProfilePublicSerializer,
)
from Users.tasks import notify_superusers_about_admin_key_request, send_admin_key_email

logger = logging.getLogger(__name__)


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
    authentication_classes = (
        []
    )  # <-- отключаем SessionAuthentication => CSRF не требуется

    @extend_schema(
        summary="Зарегистрировать нового пользователя",
        description=(
            "Создает новую учетную запись пользователя с указанной ролью (студент, преподаватель, администратор). "
            "Для регистрации администратора/модератора аккаунт будет создан, но потребует активации суперпользователем для получения ключа."
        ),
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


@extend_schema_view(
    list=extend_schema(
        summary="Список профилей",
        description="Возвращает список публичных профилей пользователей.",
    ),
    retrieve=extend_schema(
        summary="Детали профиля",
        description=(
            "Возвращает подробную информацию о профиле пользователя (публичную или приватную в зависимости от прав)."
        ),
    ),
    create=extend_schema(
        summary="Создать профиль",
        description="Создание профиля (обычно через регистрацию).",
    ),
    update=extend_schema(
        summary="Обновить профиль",
        description="Полное обновление профиля (только владелец).",
    ),
    partial_update=extend_schema(
        summary="Частично обновить профиль",
        description="Частичное обновление профиля (только владелец).",
    ),
    destroy=extend_schema(
        summary="Удалить профиль", description="Удаление профиля (только владелец)."
    ),
)
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
    lookup_value_regex = r"[^/]+"

    def get_serializer_class(self):
        if self.action == "me":
            return UserProfilePrivateSerializer
        if self.action == "request_admin_key":
            return RequestAdminKeySerializer
        if self.action == "admin_key_login":
            return AdminKeyLoginSerializer
        if self.action == "list":
            return UserProfilePublicSerializer
        # Для детальных действий (retrieve, update, partial_update, destroy)
        # Если пользователь аутентифицирован и является владельцем профиля, используем приватный сериализатор.
        # В противном случае используем публичный сериализатор.
        if getattr(self.request, "user", None) and self.request.user.is_authenticated:
            try:
                obj = self.get_object()
                if obj == self.request.user:
                    return UserProfilePrivateSerializer
            except Exception:
                pass
        return UserProfilePublicSerializer

    def get_permissions(self):
        """
        Устанавливает права доступа для различных действий.
        'me' - только авторизованный пользователь.
        'retrieve' (просмотр другого профиля) - любой авторизованный.
        'update', 'partial_update' - только владелец.
        'generate_new_admin_key' - только суперпользователь.
        'request_admin_key' - AllowAny (позволяет даже неактивным пользователям запросить ключ).
        'admin_key_login' - AllowAny, так как это специальный логин
        """
        if self.action == "me":
            self.permission_classes = [IsAuthenticated]
        elif self.action in ["update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        elif self.action == "generate_new_admin_key":
            self.permission_classes = [IsAuthenticated]
        elif self.action == "request_admin_key":
            self.permission_classes = [AllowAny]
        elif self.action == "admin_key_login":
            self.permission_classes = [AllowAny]
        elif self.action == "list":
            self.permission_classes = [IsAuthenticated]
        elif self.action == "retrieve":
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    @staticmethod
    def _extract_request_data(request):
        """Универсально извлекаем данные из DRF Request или Django WSGIRequest."""
        # DRF Request
        if hasattr(request, "data"):
            return request.data
        # Django WSGIRequest POST/PUT
        try:
            if hasattr(request, "POST") and request.POST:
                return request.POST
        except Exception:
            pass
        # Попробуйте разобрать тело JSON
        try:
            import json

            if getattr(request, "body", None):
                return json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            pass
        return {}

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
        description=(
            "Только суперпользователь может сгенерировать новый уникальный административный ключ "
            "для указанного пользователя (если его роль - администратор или модератор) и отправить его по email. "
            "Старый ключ будет деактивирован, а пользователь будет активирован, если он неактивен."
        ),
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
        data = self._extract_request_data(request)
        serializer = RequestAdminKeySerializer(data=data)
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
            AdminKey.objects.filter(user=user, is_active=True).update(is_active=False)
            new_key_value = secrets.token_urlsafe(32)
            AdminKey.objects.create(
                user=user, key=new_key_value, is_active=True, email=user.email
            )
            if not user.is_active or not user.is_admin_key_required:
                user.is_active = True
                user.is_admin_key_required = True
                user.save()
            send_admin_key_email.delay(user.email, new_key_value, user.role)
        return Response(
            {
                "detail": f"Новый админ-ключ успешно сгенерирован и отправлен на {user.email}."
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Запросить админ-ключ (для администраторов/модераторов)",
        description=(
            "Пользователь с ролью 'администратор' или 'модератор', который еще не имеет активного админ-ключа "
            "или не активировал свой аккаунт, может запросить отправку нового ключа на свой email. "
            "Запрос может быть обработан только суперпользователем."
        ),
        request=RequestAdminKeySerializer,
        responses={
            200: {"description": "Запрос на получение админ-ключа отправлен."},
            400: {
                "description": "Ошибка: неверная роль пользователя или ключ уже выдан."
            },
            404: {"description": "Пользователь не найден."},
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def request_admin_key(self, request):
        data = self._extract_request_data(request)
        serializer = RequestAdminKeySerializer(data=data)
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
        if user.has_logged_in_with_key:
            return Response(
                {
                    "detail": "Вы уже вошли с админ-ключом. Дополнительный ключ не требуется."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
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
            200: {"description": "Успешный вход. Возвращает токены доступа."},
            400: {"description": "Неверные учетные данные или админ-ключ."},
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def admin_key_login(self, request):
        data = self._extract_request_data(request)
        serializer = AdminKeyLoginSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        logger.info(
            f"Вход с помощью ключа администратора выполнен успешно: {user.email} (role: {user.role})"
        )
        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    summary="Получение JWT токенов (обмен email+password на access/refresh)",
    description="Обмен email и password на пару токенов (access и refresh).",
    request=CustomTokenObtainPairSerializer,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"access": "eyJ...", "refresh": "eyJ..."}
                }
            }
        }
    },
    examples=[
        OpenApiExample(
            "Пример запроса токена",
            value={"email": "teacher_1@a.aa", "password": "Spirocheta77"},
            request_only=True,
            media_type="application/json",
        )
    ],
)
class CustomTokenObtainView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    summary="Обновление access токена по refresh",
    description="Получение нового access токена используя refresh токен.",
    request=TokenRefreshView.serializer_class,
    responses={
        200: {"content": {"application/json": {"example": {"access": "eyJ..."}}}}
    },
)
class CustomTokenRefreshView(TokenRefreshView):
    pass
