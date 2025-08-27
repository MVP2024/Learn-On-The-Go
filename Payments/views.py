"""
Представления для системы платежей.
Здесь студенты могут покупать дисциплины и уроки, а админы настраивать цены.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from drf_spectacular.utils import extend_schema, OpenApiExample # Добавляем импорт extend_schema и OpenApiExample

from .models import Payment, PurchasedContent, PriceConfiguration
from .serializers import (
    PaymentSerializer,
    CreatePaymentSerializer,
    PurchasedContentSerializer,
    PaymentStatusSerializer,
    PriceConfigurationSerializer,
    YooKassaWebhookSerializer # Добавляем импорт нового сериализатора
)
from .services import PaymentService
from Users.permissions import IsStudent

import json
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Инициализация логгера для модуля Payments

@extend_schema(tags=['Платежи'])
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Тут можно смотреть и делать новые платежи.
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Показываем только платежи этого пользователя.
        """
        return Payment.objects.filter(user=self.request.user).order_by('-created_at')

    @extend_schema(
        summary="Создать новый платеж",
        description="Создает новый платеж за дисциплину или урок. "
                   "Если контент бесплатный, платеж автоматически завершается.",
        request=CreatePaymentSerializer,
        responses={
            201: PaymentSerializer,
            400: {'description': 'Ошибка валидации'},
        },
        examples=[
            OpenApiExample(
                'Платеж за дисциплину',
                value={
                    'payment_type': 'discipline',
                    'discipline_id': 1,
                    'payment_method': 'card'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Платеж за урок',
                value={
                    'payment_type': 'lesson',
                    'lesson_id': 1,
                    'payment_method': 'card'
                },
                request_only=True,
            )
        ]
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsStudent])
    def create_payment(self, request):
        """
        Создает новый платеж.
        """
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment = PaymentService.create_payment(
                user=request.user,
                **serializer.validated_data
            )

            response_serializer = PaymentSerializer(payment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Завершить платеж",
        description="Завершает платеж по ID транзакции (для интеграции с платежными системами).",
        request=PaymentStatusSerializer,
        responses={
            200: PaymentSerializer,
            400: {'description': 'Ошибка: платеж не найден или уже обработан'},
        }
    )
    @action(detail=False, methods=['post'])
    def complete_payment(self, request):
        """
        Завершает платеж по transaction_id.
        """
        serializer = PaymentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment = PaymentService.complete_payment(
                serializer.validated_data['transaction_id']
            )

            response_serializer = PaymentSerializer(payment)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Проверить статус платежа",
        description="Проверяет текущий статус платежа по ID транзакции.",
        responses={
            200: PaymentSerializer,
            404: {'description': 'Платеж не найден'},
        }
    )
    @action(detail=False, methods=['get'])
    def check_status(self, request):
        """
        Проверяет статус платежа по transaction_id.
        """
        transaction_id = request.query_params.get('transaction_id')
        if not transaction_id:
            return Response(
                {'error': 'Необходимо указать transaction_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Платеж не найден'},
                status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(tags=['Купленный контент'])
class PurchasedContentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Тут смотрим что студент купил.
    """
    serializer_class = PurchasedContentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Показываем только что купил этот пользователь.
        """
        return PurchasedContent.objects.filter(
            user=self.request.user
        ).select_related(
            'discipline', 'lesson', 'payment'
        ).order_by('-purchased_at')

    @extend_schema(
        summary="Проверить доступ к дисциплине",
        description="Проверяет, есть ли у пользователя доступ к указанной дисциплине.",
        responses={
            200: {'description': 'Информация о доступе'},
            400: {'description': 'Дисциплина не указана'},
        }
    )
    @action(detail=False, methods=['get'])
    def check_discipline_access(self, request):
        """
        Проверяет доступ к дисциплине по ID.
        """
        discipline_id = request.query_params.get('discipline_id')
        if not discipline_id:
            return Response(
                {'error': 'Необходимо указать discipline_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from Disciplines.models import Discipline
            discipline = Discipline.objects.get(id=discipline_id)
            has_access = PaymentService.has_access_to_discipline(request.user, discipline)

            return Response({
                'discipline_id': discipline_id,
                'discipline_title': discipline.title,
                'has_access': has_access
            })
        except Exception as e:
            if "DoesNotExist" in str(type(e)):
                return Response(
                    {'error': 'Дисциплина не найдена'},
                    status=status.HTTP_404_NOT_FOUND
                )
            raise e

    @extend_schema(
        summary="Проверить доступ к уроку",
        description="Проверяет, есть ли у пользователя доступ к указанному уроку.",
        responses={
            200: {'description': 'Информация о доступе'},
            400: {'description': 'Урок не указан'},
        }
    )
    @action(detail=False, methods=['get'])
    def check_lesson_access(self, request):
        """
        Проверяет доступ к уроку по ID.
        """
        lesson_id = request.query_params.get('lesson_id')
        if not lesson_id:
            return Response(
                {'error': 'Необходимо указать lesson_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from Lessons.models import Lesson
            lesson = Lesson.objects.get(id=lesson_id)
            has_access = PaymentService.has_access_to_lesson(request.user, lesson)

            return Response({
                'lesson_id': lesson_id,
                'lesson_title': lesson.title,
                'has_access': has_access
            })
        except Exception as e:
            if "DoesNotExist" in str(type(e)):
                return Response(
                    {'error': 'Урок не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )
            raise e


@extend_schema(tags=['Управление ценами'])
class PriceConfigurationViewSet(viewsets.ModelViewSet):
    """
    Тут админы настраивают цены.
    """
    serializer_class = PriceConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PriceConfiguration.objects.all().select_related('discipline', 'lesson')

    def get_permissions(self):
        """
        Только администраторы и модераторы могут управлять ценами.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated]
            # Дополнительная проверка в методах
        else:
            # Просмотр цен доступен всем аутентифицированным пользователям
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def perform_create(self, serializer):
        """
        Проверка прав при создании.
        """
        if not (self.request.user.is_superuser or
                self.request.user.groups.filter(name__in=['admin', 'moderator']).exists()):
            raise PermissionDenied("У вас нет прав для управления ценами")
        serializer.save()

    def perform_update(self, serializer):
        """
        Проверка прав при обновлении.
        """
        if not (self.request.user.is_superuser or
                self.request.user.groups.filter(name__in=['admin', 'moderator']).exists()):
            raise PermissionDenied("У вас нет прав для управления ценами")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """
        Проверка прав при удалении.
        """
        if not (request.user.is_superuser or
                request.user.groups.filter(name__in=['admin', 'moderator']).exists()):
            raise PermissionDenied("У вас нет прав для управления ценами")
        return super().destroy(request, *args, **kwargs)


class YooKassaWebhookView(APIView):
    authentication_classes = []  # Отключаем аутентификацию
    permission_classes = [AllowAny]  # Разрешаем доступ всем

    @extend_schema(
        summary="Webhook для ЮKassa",
        description="Принимает уведомления от ЮKassa об изменении статуса платежей. "
                    "Необходимо настроить в личном кабинете ЮKassa.",
        request=YooKassaWebhookSerializer, # Использование нового сериализатора
        responses={
            200: {'description': 'Уведомление успешно обработано'},
            400: {'description': 'Некорректный запрос или ошибка обработки'},
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            from Payments.yookassa_service import YooKassaService
            from Payments.services import PaymentService

            # Проверка подлинности уведомления (для продакшена нужно реализовать проверку подписи)
            # В тестовом режиме yookassa_service.validate_webhook_notification просто возвращает True
            if not YooKassaService.validate_webhook_notification(request.headers, request.body.decode('utf-8')):
                return Response({'error': 'Invalid webhook signature'}, status=status.HTTP_400_BAD_REQUEST)

            data = json.loads(request.body)
            event = data.get('event')
            object_data = data.get('object')

            if event == 'payment.succeeded':
                payment_id_yookassa = object_data.get('id')
                transaction_id = object_data.get('metadata', {}).get('transaction_id')
                amount = object_data.get('amount', {}).get('value')
                amount_decimal = Decimal(amount)

                # Используем transaction_id, если он есть, иначе payment_id_yookassa
                identifier = transaction_id if transaction_id else payment_id_yookassa

                try:
                    # Попытка завершить платеж через PaymentService
                    payment = PaymentService.complete_payment(identifier)
                    return Response({'status': 'Payment processed', 'payment_id': payment.id}, status=status.HTTP_200_OK)
                except Exception as e:
                    logger.error(f"Error processing payment success webhook for {identifier}: {e}")
                    return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            elif event == 'payment.canceled' or event == 'payment.failed':
                payment_id_yookassa = object_data.get('id')
                transaction_id = object_data.get('metadata', {}).get('transaction_id')
                identifier = transaction_id if transaction_id else payment_id_yookassa

                # Здесь можно обновить статус платежа в вашей БД на 'failed' или 'canceled'
                # В данной реализации PaymentService.complete_payment только завершает,
                # поэтому требуется дополнительная логика для обновления статуса на failed/canceled.
                # Можно добавить метод в PaymentService, например, `fail_payment(transaction_id)`
                #
                # Пример (потребует изменения PaymentService):
                # # try:
                # #     PaymentService.fail_payment(identifier)
                # #     return Response({'status': 'Payment failed/canceled'}, status=status.HTTP_200_OK)
                # # except Exception as e:
                # #     logger.error(f"Error processing payment failure/cancel webhook for {identifier}: {e}")
                # #     return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

                logger.warning(f"Получено уведомление о неуспешном платеже {identifier}: {event}")
                return Response({'status': f'Unhandled event: {event}'}, status=status.HTTP_200_OK)

            else:
                logger.info(f"Получено необрабатываемое событие ЮKassa: {event}")
                return Response({'status': f'Unhandled event: {event}'}, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            logger.error("Invalid JSON in YooKassa webhook request body")
            return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"General error in YooKassa webhook: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)