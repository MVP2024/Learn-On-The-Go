"""
Сервис для работы с ЮKassa.
Тут обрабатываем создание, подтверждение и отказ платежей через ЮKassa.
"""
import logging
from uuid import uuid4
from decimal import Decimal

from django.conf import settings
from yookassa import Configuration, Payment
from yookassa.domain.models import Currency

logger = logging.getLogger(__name__)


class YooKassaService:
    """
    Сервис для работы с платежными операциями ЮKassa.
    """

    def __init__(self):
        # Настраиваем конфигурацию ЮKassa
        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

        # В тестовом режиме используем специальные параметры
        if settings.YOOKASSA_TEST_MODE:
            Configuration.configure(
                account_id=settings.YOOKASSA_SHOP_ID,
                secret_key=settings.YOOKASSA_SECRET_KEY
            )

    @staticmethod
    def create_payment(amount: Decimal, description: str, return_url: str,
                       transaction_id: str = None) -> dict:
        """
        Создает платеж в ЮKassa.
        """
        try:
            # Генерируем уникальный ключ идемпотентности
            idempotence_key = str(uuid4())

            # Конвертируем amount в строку с 2 знаками после запятой
            amount_str = f"{float(amount):.2f}"

            # Формируем данные для платежа
            payment_data = {
                "amount": {
                    "value": amount_str,
                    "currency": Currency.RUB
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url
                },
                "capture": True,  # Автоматическое списание
                "description": description,
                "metadata": {
                    "transaction_id": transaction_id or str(uuid4())
                }
            }

            # Создаем платеж
            payment = Payment.create(payment_data, idempotence_key)

            logger.info(f"Создан платеж ЮKassa: {payment.id}, сумма: {amount_str}")

            return {
                'payment_id': payment.id,
                'status': payment.status,
                'confirmation_url': payment.confirmation.confirmation_url,
                'amount': amount,
                'created_at': payment.created_at,
                'metadata': payment.metadata
            }

        except Exception as e:
            logger.error(f"Ошибка создания платежа ЮKassa: {str(e)}")
            raise Exception(f"Не удалось создать платеж: {str(e)}")

    @staticmethod
    def get_payment_info(payment_id: str) -> dict:
        """
        Получает информацию о платеже.
        """
        try:
            payment = Payment.find_one(payment_id)

            return {
                'payment_id': payment.id,
                'status': payment.status,
                'amount': Decimal(payment.amount.value),
                'currency': payment.amount.currency,
                'created_at': payment.created_at,
                'metadata': payment.metadata,
                'paid': payment.paid,
                'refundable': payment.refundable
            }

        except Exception as e:
            logger.error(f"Ошибка получения информации о платеже {payment_id}: {str(e)}")
            raise Exception(f"Не удалось получить информации о платеже: {str(e)}")

    @staticmethod
    def confirm_payment(payment_id: str) -> bool:
        """
        Подтверждает платеж (если требуется ручное подтверждение).
        """
        try:
            payment = Payment.find_one(payment_id)

            if payment.status == 'waiting_for_capture':
                Payment.capture(payment_id, {
                    "amount": payment.amount
                })
                logger.info(f"Платеж {payment_id} подтвержден")
                return True

            return False

        except Exception as e:
            logger.error(f"Ошибка подтверждения платежа {payment_id}: {str(e)}")
            raise Exception(f"Не удалось подтвердить платеж: {str(e)}")

    @staticmethod
    def cancel_payment(payment_id: str, reason: str = "canceled_by_merchant") -> bool:
        """
        Отменяет платеж.
        """
        try:
            Payment.cancel(payment_id)
            logger.info(f"Платеж {payment_id} отменен по причине: {reason}")
            return True

        except Exception as e:
            logger.error(f"Ошибка отмены платежа {payment_id}: {str(e)}")
            raise Exception(f"Не удалось отменить платеж: {str(e)}")

    @staticmethod
    def create_refund(payment_id: str, amount: Decimal = None, reason: str = None) -> dict:
        """
        Создает возврат по платежу.
        """
        try:
            from yookassa import Refund

            refund_data = {
                "payment_id": payment_id
            }

            if amount:
                refund_data["amount"] = {
                    "value": f"{float(amount):.2f}",
                    "currency": Currency.RUB,
                }

            if reason:
                refund_data["description"] = str(reason)

            refund = Refund.create(refund_data)

            logger.info(f"Создан возврат для платежа {payment_id}: {refund.id}")

            return {
                'refund_id': refund.id,
                'status': refund.status,
                'amount': Decimal(refund.amount.value) if refund.amount else None,
                'created_at': refund.created_at
            }

        except Exception as e:
            logger.error(f"Ошибка создания возврата для платежа {payment_id}: {str(e)}")
            raise Exception(f"Не удалось создать возврат: {str(e)}")

    @staticmethod
    def validate_webhook_notification(headers: dict, body: str) -> bool:
        """
        Проверяет подлинность уведомления от ЮKassa.
        В реальном проекте здесь должна быть проверка подписи.
        """
        # В тестовом режиме просто возвращаем True
        if settings.YOOKASSA_TEST_MODE:
            return True

        # TODO: Добавить проверку подписи для продакшена
        # Код для проверки. Проверяем, что уведомление от юкасса пришло, а не от мошенника:
        # from yookassa.domain.notification import WebhookNotificationFactory
        #
        # try:
        #     notification_object = WebhookNotificationFactory().create(body, headers)
        #     return True
        # except Exception:
        #     return False

        return True

    @staticmethod
    def get_test_payment_data() -> dict:
        """
        Возвращает тестовые данные для разработки.
        """
        return {
            'test_card_number': '5555555555554444',  # Тестовая карта для успешных платежей
            'test_expiry': '12/26',
            'test_cvc': '123',
            'test_decline_card': '4000000000000002',  # Карта для отклонения платежа
            'webhook_url': getattr(settings, 'YOOKASSA_WEBHOOK_URL', f"{settings.BASE_URL}/api/payments/yookassa-webhook/"),
            'return_url_pattern': f"{settings.BASE_URL}/payment-success/?transaction_id={{transaction_id}}"
        }
