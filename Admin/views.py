import logging
import secrets

from django.db import transaction
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from Admin.models import AdminKey
from Admin.serializers import AdminKeySerializer
from Users.models import User
from Users.tasks import send_admin_key_email
from utils.paginators import StandardResultsSetPagination


@extend_schema_view(
    list=extend_schema(
        summary="Список admin-ключей",
        description="Возвращает список AdminKey с возможностью фильтрации по is_active, email и user.",
        responses={200: AdminKeySerializer(many=True)},
        examples=[
            OpenApiExample(
                "Пример ответа — список",
                value=[
                    {
                        "id": 1,
                        "user": None,
                        "user_email": "other@x.y",
                        "key": "ak-xxxxx",
                        "email": "other@x.y",
                        "is_active": True,
                        "created_at": "2025-09-01T12:00:00Z",
                        "expires_at": None,
                    }
                ],
                response_only=True,
                media_type="application/json",
            )
        ],
    ),
    retrieve=extend_schema(
        summary="Детали admin-ключа",
        description="Детальная информация по конкретному admin-ключу (по id).",
        responses={200: AdminKeySerializer},
        examples=[
            OpenApiExample(
                "Пример ответа — детально",
                value={
                    "id": 1,
                    "user": None,
                    "user_email": "other@x.y",
                    "key": "ak-xxxxx",
                    "email": "other@x.y",
                    "is_active": True,
                    "created_at": "2025-09-01T12:00:00Z",
                    "expires_at": None,
                },
                response_only=True,
                media_type="application/json",
            )
        ],
    ),
    revoke=extend_schema(
        summary="Деактивировать ключ",
        description="Деактивирует указанный admin-ключ (is_active -> False).",
        responses={
            200: {"application/json": {"example": {"detail": "Ключ деактивирован"}}}
        },
    ),
    reactivate=extend_schema(
        summary="Активировать ключ",
        description="Активирует указанный admin-ключ (is_active -> True).",
        responses={
            200: {"application/json": {"example": {"detail": "Ключ активирован"}}}
        },
    ),
    resend=extend_schema(
        summary="Повторно отправить ключ по email",
        description=(
            "Отправляет текущий ключ на привязанный email. Если email отсутствует — возвращает 400."
        ),
        responses={
            200: {
                "application/json": {
                    "example": {"detail": "Ключ отправлен на user@example.com"}
                }
            },
            400: {"description": "Email отсутствует"},
        },
        examples=[
            OpenApiExample(
                "Пример запроса",
                value={},
                request_only=True,
                media_type="application/json",
            ),
            OpenApiExample(
                "Пример ответа",
                value={"detail": "Ключ отправлен на user@example.com"},
                response_only=True,
                media_type="application/json",
            ),
        ],
    ),
    regenerate=extend_schema(
        summary="Регенерировать ключ",
        description=(
            "Деактивирует активные ключи для пользователя/email и создаёт новый ключ, который отправляется по email."
        ),
        responses={
            201: AdminKeySerializer,
            400: {"description": "Email отсутствует"},
        },
        examples=[
            OpenApiExample(
                "Пример ответа",
                value={
                    "id": 123,
                    "user": None,
                    "user_email": "user@example.com",
                    "key": "newly-generated-key",
                    "email": "user@example.com",
                    "is_active": True,
                    "created_at": "2025-09-02T10:00:00Z",
                    "expires_at": None,
                },
                response_only=True,
                media_type="application/json",
            )
        ],
    ),
    pending_requests=extend_schema(
        summary="Список ожидающих запросов на ключ",
        description=(
            "Возвращает пользователей, у которых is_admin_key_required=True и нет активного AdminKey."
        ),
        responses={
            200: {
                "description": "Список заявок",
            }
        },
        examples=[
            OpenApiExample(
                "Пример ответа",
                value=[{"id": 10, "email": "req@a.aa", "role": "admin"}],
                response_only=True,
                media_type="application/json",
            )
        ],
    ),
    approve_request=extend_schema(
        summary="Одобрить запрос на ключ",
        description=(
            "Принимает email в теле запроса, генерирует новый ключ для найденного пользователя и отправляет письмо."
        ),
        examples=[
            OpenApiExample(
                "Пример запроса",
                value={"email": "user@example.com"},
                request_only=True,
                media_type="application/json",
            ),
            OpenApiExample(
                "Пример ответа",
                value={"detail": "Ключ сгенерирован и отправлен на user@example.com"},
                response_only=True,
                media_type="application/json",
            ),
        ],
        responses={
            200: {
                "application/json": {
                    "example": {
                        "detail": "Ключ сгенерирован и отправлен на user@example.com"
                    }
                }
            },
            400: {"description": "email обязателен"},
            404: {"description": "Пользователь не найден"},
        },
    ),
)
@extend_schema(tags=["Admin Keys"])
class AdminKeyViewSet(viewsets.ModelViewSet):
    """Управление административными ключами. Доступ — только для админов.

    Реализованы дополнительные actions:
    - revoke (POST): деактивирует ключ
    - reactivate (POST): активирует ключ
    - regenerate (POST): деактивирует все активные ключи для пользователя/email и создаёт новый
    - resend (POST): повторно отправляет email с ключом
    - pending_requests (GET): возвращает список пользователей с is_admin_key_required=True и без активного AdminKey
    - approve_request (POST): генерирует ключ для указанного email и отправляет письмо
    """

    queryset = AdminKey.objects.all().select_related("user")
    serializer_class = AdminKeySerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        # Бережно извлекаем параметры запроса: в тестах и при прямом вызове иногда
        # self.request может быть Django HttpRequest (нет query_params), поэтому
        # используем getattr с fallback на GET.
        request = getattr(self, "request", None)
        params = {}
        if request is not None:
            params = getattr(request, "query_params", getattr(request, "GET", {})) or {}

        # простые фильтры
        is_active = params.get("is_active")
        if is_active is not None:
            if str(is_active).lower() in ("1", "true", "yes"):
                qs = qs.filter(is_active=True)
            else:
                qs = qs.filter(is_active=False)
        email = params.get("email")
        if email:
            qs = qs.filter(email__icontains=email)
        user = params.get("user")
        if user:
            qs = qs.filter(user__id=user)
        # Явно сортируем по created_at (новые первыми) чтобы пагинация была детерминированной
        try:
            return qs.order_by("-created_at")
        except Exception:
            return qs

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        adm = self.get_object()
        adm.is_active = False
        adm.save(update_fields=["is_active"])
        return Response({"detail": "Ключ деактивирован"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        adm = self.get_object()
        adm.is_active = True
        adm.save(update_fields=["is_active"])
        return Response({"detail": "Ключ активирован"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        """Повторно отправляет email с ключом. Если email отсутствует — возвращаем 400."""
        adm = self.get_object()
        email = adm.email
        if not email:
            return Response(
                {"detail": "Нет email для отправки"}, status=status.HTTP_400_BAD_REQUEST
            )
        send_admin_key_email.delay(email, adm.key, getattr(adm.user, "role", "admin"))
        return Response(
            {"detail": f"Ключ отправлен на {email}"}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """Деактивирует старые ключи и создаёт новый для того же user/email."""
        adm = self.get_object()
        user = adm.user
        email = adm.email or (user.email if user else None)
        if not email:
            return Response(
                {"detail": "Нет email для генерации ключа"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            if user:
                AdminKey.objects.filter(user=user, is_active=True).update(
                    is_active=False, user=None
                )
            else:
                AdminKey.objects.filter(email=email, is_active=True).update(
                    is_active=False
                )
            new_key = secrets.token_urlsafe(32)
            new = AdminKey.objects.create(
                user=user, key=new_key, email=email, is_active=True
            )
            send_admin_key_email.delay(email, new_key, getattr(user, "role", "admin"))
        return Response(
            AdminKeySerializer(new, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def pending_requests(self, request):
        # Пользователи, у которых is_admin_key_required=True и у которых нет активного AdminKey
        users = User.objects.filter(is_admin_key_required=True)
        users = users.exclude(admin_key__is_active=True)
        data = [
            {"id": u.id, "email": u.email, "role": getattr(u, "role", None)}
            for u in users
        ]
        return Response(data)

    @action(detail=False, methods=["post"])
    def approve_request(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"detail": "email обязателен"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            AdminKey.objects.filter(user=user, is_active=True).update(
                is_active=False, user=None
            )
            new_key = secrets.token_urlsafe(32)
            AdminKey.objects.create(
                user=user, key=new_key, email=user.email, is_active=True
            )

        try:
            send_admin_key_email.delay(
                user.email, new_key, getattr(user, "role", "admin")
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "approve_request: failed to queue send_admin_key_email"
            )

        return Response(
            {"detail": f"Ключ сгенерирован и отправлен на {user.email}"},
            status=status.HTTP_200_OK,
        )
