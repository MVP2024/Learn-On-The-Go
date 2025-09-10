import os
import sys
from decimal import Decimal

import django

# Настройка окружения Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings

from Payments.stripe_service import StripeService


def test_stripe_connection():
    """
    Тестирует подключение к Stripe.
    """
    print("=== Тестирование Stripe ===")

    # Проверяем настройки
    if not settings.STRIPE_SECRET_KEY:
        print("❌ Ошибка: Не настроен STRIPE_SECRET_KEY в .env")
        print("Добавьте в .env:")
        print("STRIPE_SECRET_KEY=sk_test_ваш_ключ")
        return False

    print(f"✅ Secret Key: {settings.STRIPE_SECRET_KEY[:12]}...")
    print(f"✅ Тестовый режим: {settings.STRIPE_TEST_MODE}")

    try:
        # Инициализируем сервис
        service = StripeService()

        # Получаем тестовые данные
        test_data = service.get_test_payment_data()
        print("\n📋 Тестовые данные:")
        print(f"Тестовая карта: {test_data['test_card_number']}")
        print(f"Срок действия: {test_data['test_expiry']}")
        print(f"CVC: {test_data['test_cvc']}")

        print("\n✅ Подключение к Stripe успешно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка подключения к Stripe: {e}")
        return False


def create_test_payment():
    """
    Создает тестовый платеж в Stripe.
    """
    print("\n=== Создание тестового платежа ===")

    try:
        service = StripeService()

        # Создаем тестовый платеж
        payment = service.create_payment_intent(
            amount=Decimal("100.00"),
            description="Тестовый платеж - Курс Python",
            transaction_id="test_123456",
        )

        print(f"✅ Платежный интент создан!")
        print(f"ID: {payment['payment_intent_id']}")
        print(f"Статус: {payment['status']}")
        print(f"Сумма: {payment['amount']} ₽")
        print(f"Client Secret: {payment['client_secret'][:20]}...")

        return payment["payment_intent_id"]

    except Exception as e:
        print(f"❌ Ошибка создания платежа: {e}")
        return None


def check_payment_status(payment_intent_id):
    """
    Проверяет статус платежа.
    """
    print(f"\n=== Проверка статуса платежа {payment_intent_id} ===")

    try:
        service = StripeService()
        payment_info = service.get_payment_info(payment_intent_id)

        print(f"✅ Информация получена!")
        print(f"Статус: {payment_info['status']}")
        print(f"Сумма: {payment_info['amount']} {payment_info['currency']}")
        print(f"Создан: {payment_info['created_at']}")

        return payment_info

    except Exception as e:
        print(f"❌ Ошибка получения информации: {e}")
        return None


def main():
    """
    Главная функция тестирования.
    """
    print("🚀 Тестирование интеграции со Stripe")
    print("=" * 50)

    # 1. Тестируем подключение
    if not test_stripe_connection():
        print("\n❌ Тестирование прервано из-за ошибок подключения")
        sys.exit(1)

    # 2. Создаем тестовый платеж
    payment_id = create_test_payment()
    if not payment_id:
        print("\n❌ Не удалось создать тестовый платеж")
        sys.exit(1)

    # 3. Проверяем статус платежа
    check_payment_status(payment_id)

    print("\n✅ Тестирование завершено!")
    print("\n📖 Следующие шаги:")
    print("1. Настройте webhook в дашборде Stripe")
    print("2. Используйте тестовые карты для проверки оплаты")
    print("3. Намного проще чем ЮKassa! 🎉")


if __name__ == "__main__":
    main()
