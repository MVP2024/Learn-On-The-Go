#!/usr/bin/env python
"""
Скрипт для очистки базы данных и загрузки фикстур.
Очищает все основные модели и загружает тестовые данные.
"""
import os
import django
from django.db import transaction
from django.core.management import call_command

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from Users.models import User
from Students.models import Student
from Teachers.models import Teacher
from Admin.models import AdminKey
from Disciplines.models import Discipline, Section
from Lessons.models import Lesson, UserLessonProgress
from Tests.models import Test, Question, Answer, QuizAttempt, Choice, QuizCategory, QuestionHint
from Payments.models import Payment, PurchasedContent, PriceConfiguration


def clear_database():
    """
    Очищает все основные модели в правильном порядке (с учетом внешних ключей).
    """
    print("=== Очистка базы данных ===")

    with transaction.atomic():
        # Очищаем в правильном порядке (сначала зависимые модели)
        models_to_clear = [
            # Платежи и связанные модели
            (PurchasedContent, "купленный контент"),
            (Payment, "платежи"),
            (PriceConfiguration, "конфигурации цен"),

            # Тесты и связанные модели
            (Choice, "выборы ответов"),
            (QuizAttempt, "попытки тестов"),
            (QuestionHint, "подсказки к вопросам"),
            (Answer, "ответы"),
            (Question, "вопросы"),
            (Test, "тесты"),
            (QuizCategory, "категории тестов"),

            # Уроки и прогресс
            (UserLessonProgress, "прогресс уроков"),
            (Lesson, "уроки"),

            # Дисциплины и разделы
            (Section, "разделы дисциплин"),
            (Discipline, "дисциплины"),

            # Пользователи и связанные модели
            (AdminKey, "админ-ключи"),
            (Student, "студенты"),
            (Teacher, "преподаватели"),
            (User, "пользователи"),
        ]

        for model, name in models_to_clear:
            count = model.objects.count()
            if count > 0:
                model.objects.all().delete()
                print(f"✅ Удалено {count} записей: {name}")
            else:
                print(f"⚪ Нет записей для удаления: {name}")


def load_fixtures():
    """
    Загружает фикстуры из файла.
    """
    print("\n=== Загрузка фикстур ===")

    try:
        call_command('loaddata', 'initial_data', verbosity=2)
        print("✅ Фикстуры успешно загружены!")
    except Exception as e:
        print(f"❌ Ошибка загрузки фикстур: {e}")
        raise


def verify_data():
    """
    Проверяет, что данные загрузились корректно.
    """
    print("\n=== Проверка загруженных данных ===")

    checks = [
        (User, "пользователи"),
        (Discipline, "дисциплины"),
        (Lesson, "уроки"),
        (Test, "тесты"),
        (Question, "вопросы"),
        (Answer, "ответы"),
        (PriceConfiguration, "конфигурации цен"),
        (Payment, "платежи"),
        (PurchasedContent, "купленный контент"),
    ]

    print("Количество записей:")
    for model, name in checks:
        count = model.objects.count()
        print(f"  {name}: {count}")

    # Проверим тестовых пользователей
    print("\nТестовые пользователи:")
    users = User.objects.all()
    for user in users:
        print(f"  📧 {user.email} (роль: {user.role})")


def main():
    """
    Главная функция скрипта.
    """
    print("🗑️  Скрипт очистки и загрузки фикстур")
    print("=" * 50)

    try:
        # Шаг 1: Очистка БД
        clear_database()

        # Шаг 2: Загрузка фикстур
        load_fixtures()

        # Шаг 3: Проверка результата
        verify_data()

        print("\n🎉 Успешно завершено!")
        print("\n📋 Данные для тестирования:")
        print("Email: admin@a.aa, teacher_1@a.aa, student_1@a.aa, moderator_1@a.aa")
        print("Пароль: Spirocheta77 (для всех)")

    except Exception as e:
        print(f"\n❌ Ошибка выполнения скрипта: {e}")
        print("Попробуйте выполнить операции вручную:")
        print("1. python clear_test_users.py  # если нужно удалить только пользователей")
        print("2. python manage.py flush --noinput  # полная очистка БД")
        print("3. python manage.py loaddata fixtures/initial_data.json")


if __name__ == "__main__":
    main()