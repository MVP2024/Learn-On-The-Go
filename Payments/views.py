import json
import logging
from decimal import Decimal

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from Payments.models import Payment, PriceConfiguration, PurchasedContent
from Payments.serializers import (
    CreatePaymentSerializer,
    PaymentSerializer,
    PaymentStatusSerializer,
    PriceConfigurationSerializer,
    PurchasedContentSerializer,
    YooKassaWebhookSerializer,
)
from Payments.services import PaymentService
from Payments.stripe_service import StripeService
from Payments.yookassa_service import YooKassaService
from Users.permissions import IsStudent

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Список платежей",
        description="Возвращает список платежей текущего пользователя (пагинация).",
        responses={200: PaymentSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Детали платежа",
        description="Возвращает детали конкретного платежа по ID.",
    ),
)
@extend_schema(tags=["Платежи"])
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Просмотр и создание платежей.
    """

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Показываем только платежи текущего пользователя."""
        return Payment.objects.filter(user=self.request.user).order_by("-created_at")

    @extend_schema(
        summary="Создать новый платеж",
        description=(
            "Создает новый платеж за дисциплину или урок. "
            "Если контент бесплатный, платеж автоматически завершается. "
            "Для платных платежей возвращается информация для завершения оплаты "
            "(yookassa_confirmation_url или stripe_client_secret)."
        ),
        request=CreatePaymentSerializer,
        responses={201: PaymentSerializer, 400: {"description": "Ошибка валидации"}},
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, IsStudent],
    )
    def create_payment(self, request):
        """Создает новый платеж и при необходимости запускает внешний платёжный flow."""
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = PaymentService.create_payment(
                user=request.user, **serializer.validated_data
            )
            # Если платеж требует внешней оплаты — создаём объект во внешней системе
            payment_method = serializer.validated_data.get("payment_method")
            if payment.status == "pending" and payment.amount > Decimal("0"):
                try:
                    if payment_method and payment_method.lower() == "yookassa":
                        yservice = YooKassaService()
                        from django.conf import settings

                        return_url = f"{settings.BASE_URL}/payment-success/?transaction_id={payment.transaction_id}"
                        payment_data = yservice.create_payment(
                            amount=Decimal(payment.amount),
                            description=f"Оплата: {payment.get_payment_type_display()}",
                            return_url=return_url,
                            transaction_id=payment.transaction_id,
                        )
                        payment.yookassa_payment_id = payment_data.get("payment_id")
                        payment.yookassa_confirmation_url = payment_data.get(
                            "confirmation_url"
                        )
                        payment.save()
                    elif payment_method and payment_method.lower() == "stripe":
                        sservice = StripeService()
                        intent = sservice.create_payment_intent(
                            amount=Decimal(payment.amount),
                            description=f"Оплата: {payment.get_payment_type_display()}",
                            transaction_id=payment.transaction_id,
                        )
                        payment.stripe_payment_intent_id = intent.get(
                            "payment_intent_id"
                        )
                        setattr(
                            payment,
                            "_stripe_client_secret",
                            intent.get("client_secret"),
                        )
                        payment.save()
                except Exception as e:
                    logger.exception("Ошибка при создании внешнего платежа: %s", e)
                    return Response(
                        {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
                    )
            response_serializer = PaymentSerializer(payment)
            response_data = response_serializer.data
            if getattr(payment, "yookassa_confirmation_url", None):
                response_data["yookassa_confirmation_url"] = (
                    payment.yookassa_confirmation_url
                )
            if getattr(payment, "_stripe_client_secret", None):
                response_data["stripe_client_secret"] = payment._stripe_client_secret
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("Ошибка при создании платежа: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Завершить платеж",
        description="Завершает платеж по transaction_id (используется платёжной системой или webhook).",
        request=PaymentStatusSerializer,
        responses={
            200: PaymentSerializer,
            400: {"description": "Ошибка: платеж не найден или уже обработан"},
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def complete_payment(self, request):
        serializer = PaymentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = PaymentService.complete_payment(
                serializer.validated_data["transaction_id"]
            )
            response_serializer = PaymentSerializer(payment)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Ошибка при завершении платежа: %s", e)
            return Response({"ошибка": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Проверить статус платежа",
        description="Проверяет статус платежа по transaction_id.",
        parameters=[
            OpenApiParameter(
                name="transaction_id",
                type=str,
                location="query",
                required=True,
                description="Transaction ID платежа (query parameter). Пример: 3fa85f64-5717-4562-b3fc-2c963f66afa6",
            )
        ],
        responses={
            200: PaymentSerializer,
            400: {"description": "Необходимо указать transaction_id"},
            404: {"description": "Платеж не найден"},
        },
    )
    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def check_status(self, request):
        transaction_id = request.query_params.get("transaction_id")
        if not transaction_id:
            return Response(
                {"error": "Необходимо указать transaction_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Payment.DoesNotExist:
            return Response(
                {"error": "Платеж не найден"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema_view(
    list=extend_schema(
        summary="Список купленного контента",
        description="Возвращает список купленного контента текущего пользователя.",
        responses={200: PurchasedContentSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Детали купленного контента",
        description="Детали записи купленного контента.",
    ),
)
@extend_schema(tags=["Купленный контент"])
class PurchasedContentViewSet(viewsets.ReadOnlyModelViewSet):
    """Просмотр купленного контента пользователем"""

    serializer_class = PurchasedContentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            PurchasedContent.objects.filter(user=self.request.user)
            .select_related("discipline", "lesson", "payment")
            .order_by("-purchased_at")
        )


@extend_schema_view(
    list=extend_schema(
        summary="Список конфигураций цен",
        description="Возвращает все конфигурации цен (админ).",
    ),
    retrieve=extend_schema(
        summary="Детали конфигурации цены", description="Детали конфигурации цены."
    ),
    create=extend_schema(
        summary="Создать конфигурацию цены",
        description="Создаёт конфигурацию цены для дисциплины или урока (админ/модератор).",
        request=PriceConfigurationSerializer,
        responses={201: PriceConfigurationSerializer},
    ),
    update=extend_schema(
        summary="Обновить конфигурацию цены",
        description="Полное обновление конфигурации цены.",
        request=PriceConfigurationSerializer,
        responses={200: PriceConfigurationSerializer},
    ),
)
@extend_schema(tags=["Управление ценами"])
class PriceConfigurationViewSet(viewsets.ModelViewSet):
    """CRUD для конфигураций цен (админская часть)."""

    serializer_class = PriceConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PriceConfiguration.objects.all().select_related("discipline", "lesson")

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [permissions.IsAuthenticated]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not (
            self.request.user.is_superuser
            or self.request.user.groups.filter(name__in=["admin", "moderator"]).exists()
        ):
            raise PermissionDenied("У вас нет прав для управления ценами")
        serializer.save()

    def perform_update(self, serializer):
        if not (
            self.request.user.is_superuser
            or self.request.user.groups.filter(name__in=["admin", "moderator"]).exists()
        ):
            raise PermissionDenied("У вас нет прав для управления ценами")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if not (
            request.user.is_superuser
            or request.user.groups.filter(name__in=["admin", "moderator"]).exists()
        ):
            raise PermissionDenied("У вас нет прав для управления ценами")
        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Override create to support upsert behaviour: if a PriceConfiguration for the same
        discipline or lesson already exists, update it instead of failing with unique constraint.
        """
        # Извлекаем discipline/lesson из входящих данных для предварительной проверки существующей конфигурации
        discipline_id = request.data.get("discipline")
        lesson_id = request.data.get("lesson")

        # проверка прав доступа: доступ только для суперпользователя/администратора/модератора
        if not (
            request.user.is_superuser
            or request.user.groups.filter(name__in=["admin", "moderator"]).exists()
        ):
            raise PermissionDenied("У вас нет прав для управления ценами")

        existing = None
        if discipline_id is not None:
            try:
                existing = PriceConfiguration.objects.filter(
                    discipline_id=int(discipline_id)
                ).first()
            except Exception:
                existing = None
        if existing is None and lesson_id is not None:
            try:
                existing = PriceConfiguration.objects.filter(
                    lesson_id=int(lesson_id)
                ).first()
            except Exception:
                existing = None

        if existing is not None:
            # Обновляем только разрешённые поля из request.data
            price = request.data.get("price")
            if price is not None:
                existing.price = price
            if "is_free" in request.data:
                existing.is_free = request.data.get("is_free")
            if "discount_price" in request.data:
                existing.discount_price = request.data.get("discount_price")
            if "discount_end_date" in request.data:
                existing.discount_end_date = request.data.get("discount_end_date")
            existing.save()
            out_ser = self.get_serializer(existing)
            return Response(out_ser.data, status=status.HTTP_200_OK)

        # в противном случае проверяем правильность и создаём новый
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return super().create(request, *args, **kwargs)


@method_decorator(csrf_exempt, name="dispatch")
@extend_schema(tags=["ЮKassa Webhook"])
class YooKassaWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Webhook для ЮKassa",
        description="Принимает уведомления от ЮKassa об изменении статуса платежей.",
        request=YooKassaWebhookSerializer,
        responses={
            200: {"description": "Уведомление успешно обработано"},
            400: {"description": "Некорректный запрос"},
        },
    )
    def post(self, request, *args, **kwargs):
        try:
            if not YooKassaService.validate_webhook_notification(
                request.headers, request.body.decode("utf-8")
            ):
                return Response(
                    {"ошибка": "Неверная подпись WebHook"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data = json.loads(request.body)
            event = data.get("event")
            object_data = data.get("object")
            if event == "payment.succeeded":
                payment_id_yookassa = object_data.get("id")
                transaction_id = object_data.get("metadata", {}).get("transaction_id")
                identifier = transaction_id if transaction_id else payment_id_yookassa
                try:
                    payment = PaymentService.complete_payment(identifier)
                    return Response(
                        {
                            "статус": "Платёж успешно обработан",
                            "payment_id": payment.id,
                        },
                        status=status.HTTP_200_OK,
                    )
                except Exception as e:
                    logger.error(
                        "Ошибка при обработке успешного платежа через WebHook %s: %s",
                        identifier,
                        e,
                    )
                    return Response(
                        {"ошибка": str(e)}, status=status.HTTP_400_BAD_REQUEST
                    )
            if event in ("payment.canceled", "payment.failed"):
                payment_id_yookassa = object_data.get("id")
                transaction_id = object_data.get("metadata", {}).get("transaction_id")
                identifier = transaction_id if transaction_id else payment_id_yookassa
                logger.warning(
                    "Получено уведомление о неуспешном платеже %s: %s",
                    identifier,
                    event,
                )
                return Response(
                    {
                        "статус": f"Платёж неуспешен или отменён: {event}",
                        "identifier": identifier,
                    },
                    status=status.HTTP_200_OK,
                )
            logger.info("Получено необрабатываемое событие ЮKassa: %s", event)
            return Response(
                {"статус": f"Необрабатываемое событие: {event}"},
                status=status.HTTP_200_OK,
            )
        except json.JSONDecodeError:
            logger.error("Неверный JSON в теле запроса WebHook YooKassa")
            return Response(
                {"ошибка": "Некорректный JSON"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Общая ошибка в YooKassa webhook: %s", e)
            return Response(
                {"ошибка": "Внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
