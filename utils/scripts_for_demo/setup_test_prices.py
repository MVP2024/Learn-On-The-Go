
"""
Настройка тестовых цен для дисциплин
"""
import os
import django
from decimal import Decimal

# Настройка окружения Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from Disciplines.models import Discipline
from Lessons.models import Lesson
from Payments.services import PriceService

def setup_test_prices():
    print("🛒 Настройка тестовых цен")
    print("=" * 30)
    
    # Ставим цены на все дисциплины
    disciplines = Discipline.objects.all()
    for discipline in disciplines:
        price = Decimal('100.00')  # 100 рублей за дисциплину
        PriceService.set_discipline_price(discipline, price)
        print(f"✅ Дисциплина '{discipline.title}': {price} ₽")
    
    # Ставим цены на все уроки 
    lessons = Lesson.objects.all()
    for lesson in lessons:
        price = Decimal('50.00')  # 50 рублей за урок
        PriceService.set_lesson_price(lesson, price)
        print(f"✅ Урок '{lesson.title}': {price} ₽")
    
    print(f"\n🎉 Настроено {disciplines.count()} дисциплин и {lessons.count()} уроков")

if __name__ == "__main__":
    setup_test_prices()