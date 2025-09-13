import logging
from decimal import Decimal

import stripe
from django.conf import settings

logger = logging.getLogger(__name__)


# noinspection PyTypeChecker
class StripeService:
    """
    Простой сервис для работы со Stripe платежами.
    """

    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    @staticmethod
    def create_payment_intent(
        amount: Decimal, description: str, transaction_id: str = None
    ) -> dict:
        """
        Создает платежный интент в Stripe.
        """
        try:
            # Stripe работает с суммой в центах
            amount_cents = int(amount * 100)

            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="rub",  # или 'usd'
                description=description,
                metadata={"transaction_id": transaction_id or "auto-generated"},
                automatic_payment_methods={
                    "enabled": True,
                },
            )

            logger.info(f"Создан Stripe PaymentIntent: {intent.id}, сумма: {amount}")

            return {
                "payment_intent_id": intent.id,
                "client_secret": intent.client_secret,
                "amount": amount,
                "status": intent.status,
                "created_at": intent.created,
                "metadata": intent.metadata,
            }

        except Exception as e:
            logger.error(f"Ошибка создания Stripe платежа: {str(e)}")
            raise Exception(f"Не удалось создать платеж: {str(e)}")

    @staticmethod
    def get_payment_info(payment_intent_id: str) -> dict:
        """
        Получает информацию о платеже.
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            return {
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount": Decimal(intent.amount)
                / 100,  # Конвертируем обратно из центов
                "currency": intent.currency,
                "created_at": intent.created,
                "metadata": intent.metadata,
            }

        except Exception as e:
            logger.error(
                f"Ошибка получения информации о платеже {payment_intent_id}: {str(e)}"
            )
            raise Exception(f"Не удалось получить информацию о платеже: {str(e)}")

    @staticmethod
    def cancel_payment(payment_intent_id: str) -> bool:
        """
        Отменяет платеж.
        """
        try:
            intent = stripe.PaymentIntent.cancel(payment_intent_id)
            logger.info(f"Платеж {payment_intent_id} отменен")
            return intent.status == "canceled"

        except Exception as e:
            logger.error(f"Ошибка отмены платежа {payment_intent_id}: {str(e)}")
            raise Exception(f"Не удалось отменить платеж: {str(e)}")

    @staticmethod
    def create_refund(
        payment_intent_id: str, amount: Decimal = None, reason: str = None
    ) -> dict:
        """
        Создает возврат по платежу.
        """
        try:
            refund_data = {"payment_intent": payment_intent_id}

            # Согласно документации Stripe: amount должен быть int в центах
            if amount:
                refund_data["amount"] = int(amount * 100)  # В центах

            # Согласно документации Stripe: reason может быть только определенными значениями
            if reason:
                refund_data["reason"] = "requested_by_customer"
                # metadata принимает словарь ключ-значение, где все значения strings
                refund_data["metadata"] = {"custom_reason": str(reason)}
            refund = stripe.Refund.create(**refund_data)

            logger.info(f"Создан возврат для платежа {payment_intent_id}: {refund.id}")

            return {
                "refund_id": refund.id,
                "status": refund.status,
                "amount": Decimal(refund.amount) / 100 if refund.amount else None,
                "created_at": refund.created,
            }

        except Exception as e:
            logger.error(
                f"Ошибка создания возврата для платежа {payment_intent_id}: {str(e)}"
            )
            raise Exception(f"Не удалось создать возврат: {str(e)}")

    @staticmethod
    def validate_webhook_signature(
        payload: bytes, sig_header: str, endpoint_secret: str
    ) -> bool:
        """
        Проверяет подпись webhook от Stripe.
        """
        try:
            stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
            return True
        except Exception as e:
            logger.warning(f"Недействительная подпись webhook: {e}")
            return False

    @staticmethod
    def get_test_payment_data() -> dict:
        """
        Возвращает тестовые данные для разработки.
        """
        return {
            "test_card_number": "4242424242424242",  # Тестовая карта Visa
            "test_expiry": "12/26",
            "test_cvc": "123",
            "test_decline_card": "4000000000000002",  # Карта для отклонения
            "webhook_url": f"{settings.BASE_URL}/api/payments/stripe-webhook/",
            "publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
        }
