import os
import django
from decimal import Decimal

# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from Payments.yookassa_service import YooKassaService

def test_yookassa():
    print("=== Тестирование ЮKassa ===")
    print(f"SHOP_ID: {settings.YOOKASSA_SHOP_ID}")
    print(f"SECRET_KEY найден: {bool(settings.YOOKASSA_SECRET_KEY)}")
    print(f"TEST_MODE: {settings.YOOKASSA_TEST_MODE}")

    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        print("❌ Ошибка: Настройки ЮKassa не найдены!")
        return

    try:
        service = YooKassaService()
        payment = service.create_payment(
            amount=Decimal('100.00'),
            description="Тестовый платеж ЮKassa",
            return_url="https://example.com/success",
            transaction_id="test_payment_123"
        )

        print("✅ Платеж успешно создан!")
        print(f"Payment ID: {payment['payment_id']}")
        print(f"Confirmation URL: {payment['confirmation_url']}")
        print(f"Status: {payment['status']}")
        print(f"Amount: {payment['amount']}")

        print("\n🎯 Что делать дальше:")
        print("1. Откройте URL в браузере:")
        print(f"   {payment['confirmation_url']}")
        print("2. Используйте тестовую карту: 5555555555554444")
        print("3. Дата: 12/26, CVC: 123")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_yookassa()