#!/usr/bin/env python
"""
Скрипт для настройки цен на дисциплины и уроки.
Запускается как отдельный скрипт с настройками Django.
"""
import os
import sys
import django
from decimal import Decimal


# Настройка окружения Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from Disciplines.models import Discipline
from Lessons.models import Lesson
from Payments.services import PriceService


def setup_sample_prices():
    """
    Настраивает примерные цены для дисциплин и уроков.
    """
    print("=== Настройка примерных цен ===")
    
    try:
        # Настройка цен для дисциплин
        disciplines = Discipline.objects.all()
        for discipline in disciplines:
            if hasattr(discipline, 'price_config'):
                print(f"Цена для дисциплины '{discipline.title}' уже настроена")
                continue
                
            price = Decimal('999.00')  # Дисциплины дороже
            print(f"Устанавливаем цену {price} ₽ для дисциплины '{discipline.title}'")
            PriceService.set_discipline_price(discipline, price)
        
        # Настройка цен для уроков
        lessons = Lesson.objects.all()
        for lesson in lessons:
            if hasattr(lesson, 'price_config'):
                print(f"Цена для урока '{lesson.title}' уже настроена")
                continue
                
            price = Decimal('149.00')  # Уроки дешевле
            print(f"Устанавливаем цену {price} ₽ для урока '{lesson.title}'")
            PriceService.set_lesson_price(lesson, price)
            
        print("\n✅ Настройка цен завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при настройке цен: {e}")
        sys.exit(1)


def make_content_free():
    """
    Делает весь контент бесплатным (для тестирования).
    """
    print("=== Установка бесплатного доступа ===")
    
    try:
        # Делаем все дисциплины бесплатными
        disciplines = Discipline.objects.all()
        for discipline in disciplines:
            print(f"Делаем дисциплину '{discipline.title}' бесплатной")
            PriceService.set_discipline_price(
                discipline, 
                price=Decimal('0.00'), 
                is_free=True
            )
        
        # Делаем все уроки бесплатными
        lessons = Lesson.objects.all()
        for lesson in lessons:
            print(f"Делаем урок '{lesson.title}' бесплатным")
            PriceService.set_lesson_price(
                lesson, 
                price=Decimal('0.00'), 
                is_free=True
            )
            
        print("\n✅ Весь контент теперь бесплатный!")
        
    except Exception as e:
        print(f"❌ Ошибка при настройке бесплатного доступа: {e}")
        sys.exit(1)


def setup_discount_example():
    """
    Настраивает пример скидки на контент.
    """
    print("=== Настройка примера скидки ===")
    
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Берем первую дисциплину для примера скидки
        discipline = Discipline.objects.first()
        if discipline:
            end_date = timezone.now() + timedelta(days=7)  # Скидка на неделю
            
            print(f"Настраиваем скидку для дисциплины '{discipline.title}'")
            PriceService.set_discipline_price(
                discipline,
                price=Decimal('999.00'),
                discount_price=Decimal('699.00'),
                discount_end_date=end_date
            )
            print(f"Скидка: с 999 ₽ до 699 ₽ до {end_date.strftime('%Y-%m-%d %H:%M')}")
        
        # Берем первый урок для примера скидки
        lesson = Lesson.objects.first()
        if lesson:
            end_date = timezone.now() + timedelta(days=3)  # Скидка на 3 дня
            
            print(f"Настраиваем скидку для урока '{lesson.title}'")
            PriceService.set_lesson_price(
                lesson,
                price=Decimal('149.00'),
                discount_price=Decimal('99.00'),
                discount_end_date=end_date
            )
            print(f"Скидка: с 149 ₽ до 99 ₽ до {end_date.strftime('%Y-%m-%d %H:%M')}")
            
        print("\n✅ Примеры скидок настроены!")
        
    except Exception as e:
        print(f"❌ Ошибка при настройке скидок: {e}")
        sys.exit(1)


def show_help():
    """
    Показывает справку по использованию скрипта.
    """
    print("""
Использование: python utils/setup_prices.py [команда]

Команды:
  setup     - Настроить примерные цены для всего контента
  free      - Сделать весь контент бесплатным
  discount  - Настроить примеры скидок
  help      - Показать эту справку

Примеры:
  python utils/setup_prices.py setup
  python utils/setup_prices.py free
  python utils/setup_prices.py discount
    """)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        setup_sample_prices()
    elif command == "free":
        make_content_free()
    elif command == "discount":
        setup_discount_example()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Неизвестная команда: {command}")
        show_help()
        sys.exit(1)