from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import logging

from Payments.models import Payment, PriceConfiguration, PurchasedContent
from Users.models import User
from Lessons.models import UserLessonProgress
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_payments():
    """
    Очищает просроченные платежи (старше 24 часов в статусе pending)
    """
    expired_time = timezone.now() - timedelta(hours=24)
    expired_payments = Payment.objects.filter(
        status='pending',
        created_at__lt=expired_time
    )

    count = expired_payments.count()
    expired_payments.update(status='failed')

    logger.info(f"Помечены как неудачные {count} просроченных платежей")
    return f"Обработано {count} платежей"


@shared_task
def cleanup_expired_discounts():
    """
    Убирает истёкшие скидки
    """
    expired_configs = PriceConfiguration.objects.filter(
        discount_end_date__lt=timezone.now(),
        discount_price__isnull=False
    )

    count = expired_configs.count()
    expired_configs.update(
        discount_price=None,
        discount_end_date=None
    )

    logger.info(f"Убраны скидки для {count} товаров")
    return f"Обработано {count} скидок"


@shared_task
def generate_daily_reports():
    """
    Генерирует ежедневные отчёты о платежах
    """
    yesterday = timezone.now() - timedelta(days=1)
    payments_count = Payment.objects.filter(
        created_at__date=yesterday.date()
    ).count()

    completed_payments = Payment.objects.filter(
        completed_at__date=yesterday.date(),
        status='completed'
    )

    revenue = sum(p.amount for p in completed_payments)

    # Отправляем отчёт админам
    admins = User.objects.filter(is_superuser=True, is_active=True)
    admin_emails = [admin.email for admin in admins]

    if admin_emails:
        subject = f"Ежедневный отчёт - {yesterday.strftime('%Y-%m-%d')}"
        message = f"""
Статистика за {yesterday.strftime('%d.%m.%Y')}:

💰 Создано платежей: {payments_count}
✅ Завершено платежей: {completed_payments.count()}  
💵 Выручка: {revenue} ₽

Хорошего дня!
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            admin_emails,
            fail_silently=False
        )

    return f"Отчёт отправлен {len(admin_emails)} админам"


@shared_task
def update_user_progress_stats():
    """
    Обновляет статистику прогресса пользователей
    """
    students = User.objects.filter(groups__name='student')

    for student in students:
        completed_lessons = UserLessonProgress.objects.filter(
            user=student,
            is_completed=True
        ).count()

        total_watched_time = sum(
            progress.watched_duration
            for progress in UserLessonProgress.objects.filter(user=student)
        )

        # Здесь можно сохранить статистику в отдельную модель
        logger.info(f"Студент {student.email}: завершил {completed_lessons} уроков, всего {total_watched_time} сек")

    return f"Обновлена статистика для {students.count()} студентов"


@shared_task
def send_course_reminders():
    """
    Отправляет напоминания студентам о незавершённых курсах
    """
    week_ago = timezone.now() - timedelta(days=7)

    students_to_remind = User.objects.filter(
        groups__name='student',
        last_login__lt=week_ago,
        purchased_content__isnull=False
    ).distinct()

    count = 0
    for student in students_to_remind:
        purchased = PurchasedContent.objects.filter(user=student)

        if purchased.exists():
            subject = "Не забывайте про ваши курсы!"
            message = f"""
Привет, {student.first_name}!

Вы давно не заходили на платформу. У вас есть доступ к курсам:
{', '.join([p.discipline.title if p.discipline else p.lesson.title for p in purchased[:3]])}

Продолжайте обучение: {settings.BASE_URL}

Удачи в учёбе!
            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [student.email],
                fail_silently=True
            )
            count += 1

    return f"Отправлено напоминаний: {count}"


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def process_payment_completion(self, payment_id):
    """
    Обрабатывает завершение платежа с автоповтором в случае ошибок
    """
    from Payments.models import Payment
    from Payments.services import PaymentService

    try:
        payment = Payment.objects.get(id=payment_id)

        if payment.status == 'pending':
            # Проверяем платеж в ЮKassa/Stripe
            # если yookassa_payment_id отсутствует, это может быть платеж из другой системы
            # или бесплатный платеж.
            if hasattr(payment, 'yookassa_payment_id') and payment.yookassa_payment_id:
                # Если есть ID ЮKassa, используем его для проверки
                from Payments.yookassa_service import YooKassaService
                yookassa_service = YooKassaService()
                yookassa_payment_info = yookassa_service.get_payment_info(payment.yookassa_payment_id)

                if yookassa_payment_info['status'] == 'succeeded':
                    PaymentService.complete_payment(payment.transaction_id)
                    logger.info(f"Платеж {payment_id} успешно завершён")
                    return f"Payment {payment_id} completed successfully"
                elif yookassa_payment_info['status'] == 'canceled':
                    payment.status = 'failed' # Или canceled
                    payment.save()
                    logger.warning(f"Платеж {payment_id} отменен в ЮKassa")
                    return f"Payment {payment_id} canceled in YooKassa"
                elif yookassa_payment_info['status'] == 'pending':
                    logger.info(f"Платеж {payment_id} все еще в процессе в ЮKassa")
                    return f"Payment {payment_id} still pending in YooKassa"
            else:
                # Если нет yookassa_payment_id, предполагаем, что это Stripe или бесплатный платеж
                # и просто пытаемся завершить его по transaction_id
                PaymentService.complete_payment(payment.transaction_id)
                logger.info(f"Платеж {payment_id} успешно завершён")
                return f"Payment {payment_id} completed successfully"

        return f"Payment {payment_id} not ready for completion"

    except Payment.DoesNotExist:
        logger.error(f"Платеж {payment_id} не найден")
        return f"Payment {payment_id} not found"
    except Exception as exc:
        logger.error(f"Ошибка обработки платежа {payment_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def send_payment_success_notification(payment_id):
    """
    Отправляет уведомление об успешной оплате
    """
    from Payments.models import Payment
    from django.core.mail import send_mail

    try:
        payment = Payment.objects.select_related('user', 'discipline', 'lesson').get(id=payment_id)

        if payment.status == 'completed':
            content_name = payment.discipline.title if payment.discipline else payment.lesson.title

            subject = f"✅ Оплата успешно завершена - {content_name}"
            message = f"""
Здравствуйте, {payment.user.first_name}!

Ваша оплата успешно обработана:

📚 Контент: {content_name}
💰 Сумма: {payment.amount} ₽
📅 Дата: {payment.completed_at.strftime('%d.%m.%Y %H:%M')}

Теперь у вас есть полный доступ к материалам!

Перейти к обучению: {settings.BASE_URL}

С наилучшими пожеланиями,
Команда LearningPlatform
            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [payment.user.email],
                fail_silently=False
            )

            logger.info(f"Уведомление об оплате отправлено пользователю {payment.user.email}")
            return f"Notification sent to {payment.user.email}"

    except Payment.DoesNotExist:
        logger.error(f"Платеж {payment_id} не найден")
        return f"Payment {payment_id} not found"


@shared_task
def generate_payment_analytics():
    """
    Генерирует аналитику по платежам
    """
    from django.db.models import Sum, Count

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Статистика по периодам
    stats = {
        'today': Payment.objects.filter(
            completed_at__date=today,
            status='completed'
        ).aggregate(
            count=Count('id'),
            sum=Sum('amount')
        ),
        'week': Payment.objects.filter(
            completed_at__date__gte=week_ago,
            status='completed'
        ).aggregate(
            count=Count('id'),
            sum=Sum('amount')
        ),
        'month': Payment.objects.filter(
            completed_at__date__gte=month_ago,
            status='completed'
        ).aggregate(
            count=Count('id'),
            sum=Sum('amount')
        )
    }

    # Самые популярные курсы
    popular_disciplines = PurchasedContent.objects.filter(
        discipline__isnull=False,
        purchased_at__date__gte=month_ago
    ).values(
        'discipline__title'
    ).annotate(
        purchases=Count('id')
    ).order_by('-purchases')[:5]

    logger.info("Аналитика платежей сгенерирована")
    logger.info(f"За сегодня: {stats['today']['count']} платежей на {stats['today']['sum'] or 0} ₽")
    logger.info(f"За неделю: {stats['week']['count']} платежей на {stats['week']['sum'] or 0} ₽")
    logger.info(f"За месяц: {stats['month']['count']} платежей на {stats['month']['sum'] or 0} ₽")

    return {
        'stats': stats,
        'popular_disciplines': list(popular_disciplines)
    }