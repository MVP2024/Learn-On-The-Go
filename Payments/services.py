import logging
import uuid
from decimal import Decimal

from django.db import IntegrityError, models, transaction
from django.utils import timezone
from rest_framework import serializers

from Disciplines.models import Discipline
from Lessons.models import Lesson
from Payments.models import Payment, PriceConfiguration, PurchasedContent

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Тут все функции для покупки уроков и дисциплин.
    (Дублирует логику в Payments.services для тестирования/локальной разработки.)
    """

    @staticmethod
    @transaction.atomic
    def create_payment(
        user, payment_type, discipline_id=None, lesson_id=None, payment_method=None
    ):
        """
        Создаем новый платеж.
        """
        # Инициализация переменных
        discipline = None
        lesson = None
        amount = None
        # Валидация и получение объектов
        if payment_type == "discipline":
            try:
                discipline = Discipline.objects.get(id=discipline_id)
            except Discipline.DoesNotExist:
                raise serializers.ValidationError("Дисциплина не найдена")
            # Проверяем, не купил ли уже пользователь эту дисциплину
            if PurchasedContent.objects.filter(
                user=user, discipline=discipline
            ).exists():
                raise serializers.ValidationError("Вы уже приобрели эту дисциплину")
            # Получаем цену дисциплины
            try:
                price_config = PriceConfiguration.objects.get(discipline=discipline)
                amount = price_config.get_current_price()
            except PriceConfiguration.DoesNotExist:
                raise serializers.ValidationError(
                    "Цена для этой дисциплины не настроена"
                )
        elif payment_type == "lesson":
            try:
                lesson = Lesson.objects.get(id=lesson_id)
            except Lesson.DoesNotExist:
                raise serializers.ValidationError("Урок не найден")
            # Проверяем, не купил ли уже пользователь этот урок
            if PurchasedContent.objects.filter(user=user, lesson=lesson).exists():
                raise serializers.ValidationError("Вы уже приобрели этот урок")
            # Проверяем, не купил ли уже пользователь всю дисциплину
            if PurchasedContent.objects.filter(
                user=user, discipline=lesson.discipline
            ).exists():
                raise serializers.ValidationError(
                    "Вы уже приобрели всю дисциплину, к которой относится этот урок"
                )
            # Получаем цену урока
            try:
                price_config = PriceConfiguration.objects.get(lesson=lesson)
                amount = price_config.get_current_price()
            except PriceConfiguration.DoesNotExist:
                raise serializers.ValidationError("Цена для этого урока не настроена")
        else:
            raise serializers.ValidationError("Неверный тип платежа")
        # Если контент бесплатный, создаем "успешный" платеж сразу
        if amount == Decimal("0"):
            payment = Payment.objects.create(
                user=user,
                payment_type=payment_type,
                discipline=discipline,
                lesson=lesson,
                amount=amount,
                status="completed",
                payment_method=payment_method or "free",
                transaction_id=str(uuid.uuid4()),
                completed_at=timezone.now(),
            )
            # Сразу создаем запись о купленном контенте
            try:
                PurchasedContent.objects.get_or_create(
                    payment=payment,
                    defaults={
                        "user": user,
                        "discipline": discipline,
                        "lesson": lesson,
                    },
                )
            except IntegrityError:
                try:
                    PurchasedContent.objects.get(payment=payment)
                except PurchasedContent.DoesNotExist:
                    # Логируем и пробрасываем, потому что это означает неожиданное состояние
                    logger.exception(
                        "Ошибка после IntegrityError: PurchasedContent не найден для payment=%s",
                        payment.id,
                    )
                    raise
            return payment
        # Создаем платеж в состоянии pending
        payment = Payment.objects.create(
            user=user,
            payment_type=payment_type,
            discipline=discipline,
            lesson=lesson,
            amount=amount,
            status="pending",
            payment_method=payment_method,
            transaction_id=str(uuid.uuid4()),
        )
        return payment

    @staticmethod
    @transaction.atomic
    def complete_payment(transaction_id):
        """
        Завершаем платеж. Этот метод идемпотентен: повторный вызов для уже завершённого платежа просто вернёт объект.
        """
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Платеж не найден")
        # Если платеж уже завершён — безопасно вернуть его (идемпотентность)
        if payment.status == "completed":
            return payment
        if payment.status != "pending":
            raise serializers.ValidationError(
                f"Нельзя завершить платеж с текущим статусом: {payment.status}"
            )
        # Обновляем статус платежа
        payment.status = "completed"
        payment.completed_at = timezone.now()
        payment.save()
        # Создаем запись о купленном контенте (защищаемся от гонки)
        try:
            PurchasedContent.objects.get_or_create(
                payment=payment,
                defaults={
                    "user": payment.user,
                    "discipline": payment.discipline,
                    "lesson": payment.lesson,
                },
            )
        except IntegrityError:
            # Редкая ситуация: параллельный INSERT после предварительного SELECT внутри get_or_create
            try:
                PurchasedContent.objects.get(payment=payment)
            except PurchasedContent.DoesNotExist:
                logger.exception(
                    "После IntegrityError не удалось найти PurchasedContent для payment=%s",
                    payment.id,
                )
                raise
        return payment

    @staticmethod
    def get_user_purchased_content(user):
        """
        Получаем все что купил пользователь.
        """
        return PurchasedContent.objects.filter(user=user).select_related(
            "discipline", "lesson", "payment"
        )

    @staticmethod
    def has_access_to_discipline(user, discipline):
        """
        Проверяем купил ли студент дисциплину.
        """
        # Проверяем, купил ли пользователь дисциплину
        return PurchasedContent.objects.filter(
            user=user, discipline=discipline
        ).exists()

    @staticmethod
    def has_access_to_lesson(user, lesson):
        """
        Проверяем есть ли доступ к уроку.
        """
        # Проверяем, купил ли пользователь урок напрямую или всю дисциплину
        return (
            PurchasedContent.objects.filter(user=user)
            .filter(models.Q(lesson=lesson) | models.Q(discipline=lesson.discipline))
            .exists()
        )

    @staticmethod
    def get_available_tests_for_user(user, lesson=None, discipline=None):
        """
        Возвращает Test queryset, доступные пользователю.
        ВАЖНО: покупка дисциплины/урока больше НЕ даёт автоматического доступа к тестам.
        Тесты доступны только если студент завершил соответствующий урок (для тестов, привязанных к уроку)
        или завершил все уроки дисциплины (для итоговых/дисциплинарных тестов).
        """
        from django.db.models import Count, F, Q

        from Exercises.models import Test
        from Lessons.models import UserLessonProgress

        # Для указанного урока: тесты доступны только если студент завершил урок
        if lesson is not None:
            completed = UserLessonProgress.objects.filter(
                user=user, lesson=lesson, is_completed=True
            ).exists()
            if completed:
                return Test.objects.filter(lesson=lesson)
            return Test.objects.none()
        # Для дисциплины: итоговый тест (lesson is null) доступен только если студент завершил все уроки дисциплины
        if discipline is not None:
            completed_disciplines_qs = (
                Discipline.objects.annotate(
                    total_lessons=Count("lessons", distinct=True),
                    completed_lessons=Count(
                        "lessons__user_progresses",
                        filter=Q(
                            lessons__user_progresses__user=user,
                            lessons__user_progresses__is_completed=True,
                        ),
                        distinct=True,
                    ),
                )
                .filter(total_lessons__gt=0, total_lessons=F("completed_lessons"))
                .values_list("id", flat=True)
            )
            if discipline.id in list(completed_disciplines_qs):
                return Test.objects.filter(lesson__isnull=True, discipline=discipline)
            return Test.objects.none()
        # Фолбэк: если не указаны ни lesson ни discipline — возвращаем пустой queryset
        return Test.objects.none()


class PriceService:
    """
    Тут функции для управления ценами.
    """

    @staticmethod
    def set_discipline_price(
        discipline, price, is_free=False, discount_price=None, discount_end_date=None
    ):
        """
        Ставим цену для дисциплины.
        """
        price_config, created = PriceConfiguration.objects.get_or_create(
            discipline=discipline,
            defaults={
                "price": price,
                "is_free": is_free,
                "discount_price": discount_price,
                "discount_end_date": discount_end_date,
            },
        )
        if not created:
            price_config.price = price
            price_config.is_free = is_free
            price_config.discount_price = discount_price
            price_config.discount_end_date = discount_end_date
            price_config.save()
        return price_config

    @staticmethod
    def set_lesson_price(
        lesson, price, is_free=False, discount_price=None, discount_end_date=None
    ):
        """
        Ставим цену для урока.
        """
        price_config, created = PriceConfiguration.objects.get_or_create(
            lesson=lesson,
            defaults={
                "price": price,
                "is_free": is_free,
                "discount_price": discount_price,
                "discount_end_date": discount_end_date,
            },
        )
        if not created:
            price_config.price = price
            price_config.is_free = is_free
            price_config.discount_price = discount_price
            price_config.discount_end_date = discount_end_date
            price_config.save()
        return price_config
