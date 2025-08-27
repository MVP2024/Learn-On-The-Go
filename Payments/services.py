"""
Сервисы для работы с платежами.
Здесь находится вся логика покупки дисциплин и уроков, проверка доступа и управление ценами.
"""
import uuid
from django.db import transaction, models
from django.utils import timezone
from rest_framework import serializers
from .models import Payment, PurchasedContent, PriceConfiguration
from Disciplines.models import Discipline
from Lessons.models import Lesson
from Tests.models import Test
class PaymentService:
    """
    Тут все функции для покупки уроков и дисциплин.
    """

    @staticmethod
    @transaction.atomic
    def create_payment(user, payment_type, discipline_id=None, lesson_id=None, payment_method=None):
        """
        Создаем новый платеж.
        """
        # Инициализация переменных
        discipline = None
        lesson = None
        amount = None

        # Валидация и получение объектов
        if payment_type == 'discipline':
            try:
                discipline = Discipline.objects.get(id=discipline_id)
            except Discipline.DoesNotExist:
                raise serializers.ValidationError("Дисциплина не найдена")

            # Проверяем, не купил ли уже пользователь эту дисциплину
            if PurchasedContent.objects.filter(user=user, discipline=discipline).exists():
                raise serializers.ValidationError("Вы уже приобрели эту дисциплину")

            # Получаем цену дисциплины
            try:
                price_config = PriceConfiguration.objects.get(discipline=discipline)
                amount = price_config.get_current_price()
            except PriceConfiguration.DoesNotExist:
                raise serializers.ValidationError("Цена для этой дисциплины не настроена")

        elif payment_type == 'lesson':
            try:
                lesson = Lesson.objects.get(id=lesson_id)
            except Lesson.DoesNotExist:
                raise serializers.ValidationError("Урок не найден")

            # Проверяем, не купил ли уже пользователь этот урок
            if PurchasedContent.objects.filter(user=user, lesson=lesson).exists():
                raise serializers.ValidationError("Вы уже приобрели этот урок")

            # Проверяем, не купил ли уже пользователь всю дисциплину
            if PurchasedContent.objects.filter(user=user, discipline=lesson.discipline).exists():
                raise serializers.ValidationError("Вы уже приобрели всю дисциплину, к которой относится этот урок")

            # Получаем цену урока
            try:
                price_config = PriceConfiguration.objects.get(lesson=lesson)
                amount = price_config.get_current_price()
            except PriceConfiguration.DoesNotExist:
                raise serializers.ValidationError("Цена для этого урока не настроена")

        else:
            raise serializers.ValidationError("Неверный тип платежа")
        # Если контент бесплатный, создаем "успешный" платеж сразу
        if amount == 0:
            payment = Payment.objects.create(
                user=user,
                payment_type=payment_type,
                discipline=discipline,
                lesson=lesson,
                amount=amount,
                status='completed',
                payment_method=payment_method or 'free',
                transaction_id=str(uuid.uuid4()),
                completed_at=timezone.now()
            )
            
            # Сразу создаем запись о купленном контенте
            PurchasedContent.objects.create(
                user=user,
                discipline=discipline,
                lesson=lesson,
                payment=payment
            )
            
            return payment

        # Создаем платеж в состоянии pending
        payment = Payment.objects.create(
            user=user,
            payment_type=payment_type,
            discipline=discipline,
            lesson=lesson,
            amount=amount,
            status='pending',
            payment_method=payment_method,
            transaction_id=str(uuid.uuid4())
        )

        return payment

    @staticmethod
    @transaction.atomic
    def complete_payment(transaction_id):
        """
        Завершаем платеж.
        """
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Платеж не найден")
        
        if payment.status != 'pending':
            raise serializers.ValidationError("Платеж уже обработан")
        
        # Обновляем статус платежа
        payment.status = 'completed'
        payment.completed_at = timezone.now()
        payment.save()
        
        # Создаем запись о купленном контенте
        PurchasedContent.objects.create(
            user=payment.user,
            discipline=payment.discipline,
            lesson=payment.lesson,
            payment=payment
        )
        
        return payment

    @staticmethod
    def get_user_purchased_content(user):
        """
        Получаем все что купил пользователь.
        """
        return PurchasedContent.objects.filter(user=user).select_related(
            'discipline', 'lesson', 'payment'
        )

    @staticmethod
    def has_access_to_discipline(user, discipline):
        """
        Проверяем купил ли студент дисциплину.
        """
        # Проверяем, купил ли пользователь дисциплину
        return PurchasedContent.objects.filter(
            user=user,
            discipline=discipline
        ).exists()

    @staticmethod
    def has_access_to_lesson(user, lesson):
        """
        Проверяем есть ли доступ к уроку.
        """
        # Проверяем, купил ли пользователь урок напрямую или всю дисциплину
        return PurchasedContent.objects.filter(
            user=user
        ).filter(
            models.Q(lesson=lesson) | models.Q(discipline=lesson.discipline)
        ).exists()

    @staticmethod
    def get_available_tests_for_user(user, lesson=None, discipline=None):
        """
        Получаем доступные тесты для пользователя.
        """

        if lesson:
            # Если указан урок, проверяем доступ к нему
            if PaymentService.has_access_to_lesson(user, lesson):
                return Test.objects.filter(lesson=lesson)
            else:
                return Test.objects.none()

        elif discipline:
            # Если указана дисциплина, проверяем доступ к ней
            if PaymentService.has_access_to_discipline(user, discipline):
                return Test.objects.filter(discipline=discipline)
            else:
                # Возвращаем тесты только для купленных уроков этой дисциплины
                purchased_lessons = PurchasedContent.objects.filter(
                    user=user,
                    lesson__discipline=discipline
                ).values_list('lesson_id', flat=True)

                return Test.objects.filter(lesson_id__in=purchased_lessons)

        return Test.objects.none()


class PriceService:
    """
    Тут функции для управления ценами.
    """

    @staticmethod
    def set_discipline_price(discipline, price, is_free=False, discount_price=None, discount_end_date=None):
        """
        Ставим цену для дисциплины.
        """
        price_config, created = PriceConfiguration.objects.get_or_create(
            discipline=discipline,
            defaults={
                'price': price,
                'is_free': is_free,
                'discount_price': discount_price,
                'discount_end_date': discount_end_date
            }
        )
        
        if not created:
            price_config.price = price
            price_config.is_free = is_free
            price_config.discount_price = discount_price
            price_config.discount_end_date = discount_end_date
            price_config.save()
        
        return price_config

    @staticmethod
    def set_lesson_price(lesson, price, is_free=False, discount_price=None, discount_end_date=None):
        """
        Ставим цену для урока.
        """
        price_config, created = PriceConfiguration.objects.get_or_create(
            lesson=lesson,
            defaults={
                'price': price,
                'is_free': is_free,
                'discount_price': discount_price,
                'discount_end_date': discount_end_date
            }
        )
        
        if not created:
            price_config.price = price
            price_config.is_free = is_free
            price_config.discount_price = discount_price
            price_config.discount_end_date = discount_end_date
            price_config.save()
        
        return price_config