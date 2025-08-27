#!/usr/bin/env python
"""
Скрипт для тестирования интеграции с ЮKassa.
Запускается отдельно для проверки работы платежной системы.
"""
import os
import sys
import django
from decimal import Decimal

# Настройка окружения Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from Payments.yookassa_service import YooKassaService
from django.conf import settings


def test_yookassa_connection():
    """
    Тестирует подключение к ЮKassa.
    """
    print("=== Тестирование ЮKassa ===")
    
    # Проверяем настройки
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        print("❌ Ошибка: Не настроены ключи ЮKassa в .env")
        print("Добавьте в .env:")
        print("YOOKASSA_SHOP_ID=ваш_shop_id") 
        print("YOOKASSA_SECRET_KEY=ваш_секретный_ключ")
        return False
    
    print(f"✅ Shop ID: {settings.YOOKASSA_SHOP_ID}")
    print(f"✅ Тестовый режим: {settings.YOOKASSA_TEST_MODE}")
    
    try:
        # Инициализируем сервис
        service = YooKassaService()
        
        # Получаем тестовые данные
        test_data = service.get_test_payment_data()
        print("\n📋 Тестовые данные:")
        print(f"Тестовая карта: {test_data['test_card_number']}")
        print(f"Срок действия: {test_data['test_expiry']}")
        print(f"CVC: {test_data['test_cvc']}")
        
        print("\n✅ Подключение к ЮKassa успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к ЮKassa: {e}")
        return False


def create_test_payment():
    """
    Создает тестовый платеж.
    """
    print("\n=== Создание тестового платежа ===")
    
    try:
        service = YooKassaService()
        
        # Создаем тестовый платеж
        payment = service.create_payment(
            amount=Decimal('100.00'),
            description="Тестовый платеж - Курс Python",
            return_url="https://example.com/success",
            transaction_id="test_123456"
        )
        
        print(f"✅ Платеж создан!")
        print(f"ID платежа: {payment['payment_id']}")
        print(f"Статус: {payment['status']}")
        print(f"Сумма: {payment['amount']} ₽")
        print(f"URL для оплаты: {payment['confirmation_url']}")
        
        return payment['payment_id']
        
    except Exception as e:
        print(f"❌ Ошибка создания платежа: {e}")
        return None


def check_payment_status(payment_id):
    """
    Проверяет статус платежа.
    """
    print(f"\n=== Проверка статуса платежа {payment_id} ===")
    
    try:
        service = YooKassaService()
        payment_info = service.get_payment_info(payment_id)
        
        print(f"✅ Информация получена!")
        print(f"Статус: {payment_info['status']}")
        print(f"Сумма: {payment_info['amount']} {payment_info['currency']}")
        print(f"Оплачен: {'Да' if payment_info['paid'] else 'Нет'}")
        print(f"Можно вернуть: {'Да' if payment_info['refundable'] else 'Нет'}")
        
        return payment_info
        
    except Exception as e:
        print(f"❌ Ошибка получения информации: {e}")
        return None


def main():
    """
    Главная функция тестирования.
    """
    print("🚀 Тестирование интеграции с ЮKassa")
    print("=" * 50)
    
    # 1. Тестируем подключение
    if not test_yookassa_connection():
        print("\n❌ Тестирование прервано из-за ошибок подключения")
        sys.exit(1)
    
    # 2. Создаем тестовый платеж
    payment_id = create_test_payment()
    if not payment_id:
        print("\n❌ Не удалось создать тестовый платеж")
        sys.exit(1)
    
    # 3. Проверяем статус платежа
    payment_info = check_payment_status(payment_id)
    if payment_info:
        print(f"\n🎯 Для завершения теста откройте URL для оплаты в браузере")
        print(f"После оплаты снова запустите: check_payment_status('{payment_id}')")
    
    print("\n✅ Тестирование завершено!")
    print("\n📖 Следующие шаги:")
    print("1. Настройте webhook в личном кабинете ЮKassa")
    print("2. Протестируйте реальную оплату с тестовыми картами")
    print("3. Для продакшена смените YOOKASSA_TEST_MODE=False")


if __name__ == "__main__":
    main()