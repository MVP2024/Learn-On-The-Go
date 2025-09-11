import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


try:
    from celery import shared_task as _shared_task  # type: ignore
except Exception:
    _shared_task = None


def _now():
    """Возвращает timezone-aware now() если Django доступен, иначе datetime.now()."""
    try:
        from django.utils import timezone as dj_timezone  # type: ignore

        return dj_timezone.now()
    except Exception:
        return datetime.now()


class TaskWrapper:
    """Обёртка, которая предоставляет callable для прямого вызова и .delay/.apply_async методы для Celery.

    - impl: синхронная реализация функции (обычный Python callable)
    - celery_task: объект задачи Celery (если зарегистрирован), иначе None
    """

    def __init__(self, impl: Callable[..., Any], celery_task: Optional[Any] = None):
        self._impl = impl
        self._celery_task = celery_task

        def _run_fn(passed_self, *args, **kwargs):
            # Ожидается, что passed_self будет экземпляром TaskWrapper (или задачей Celery, если она привязана)
            try:
                # Вызываем базовую реализацию с помощью *args, **kwargs (impl ожидает реальные аргументы, а не self)
                return self._impl(*args, **kwargs)
            except Exception as exc:
                # Если у нас есть связанная celery-задача с методом retry — вызываем его и
                # позволяем любым исключениям оттуда проброситься наружу.
                if self._celery_task is not None and hasattr(
                    self._celery_task, "retry"
                ):
                    # намеренно не перехватываем исключения из celery_task.retry
                    return self._celery_task.retry(exc=exc)

                # Если celery retry отсутствует или недоступен — используем fallback на wrapper.retry
                try:
                    return self.retry(exc=exc)
                except Exception:
                    # Если повторная попытка не помогла, повторно вызовем исходное исключение
                    raise

        # Назначаем run обычной функцией в экземпляре, чтобы тесты могли исправлять/запускать её с явным указанием self
        self.run = _run_fn

    def __call__(self, *args, **kwargs):
        # Прямой вызов выполняет синхронную реализацию
        return self._impl(*args, **kwargs)

    def delay(self, *args, **kwargs):
        # Если есть celery task — используем её
        if self._celery_task is not None and hasattr(self._celery_task, "delay"):
            return self._celery_task.delay(*args, **kwargs)
        # Иначе выполняем синхронно и возвращаем результат
        return self._impl(*args, **kwargs)

    def apply_async(self, *args, **kwargs):
        if self._celery_task is not None and hasattr(self._celery_task, "apply_async"):
            return self._celery_task.apply_async(*args, **kwargs)
        return self._impl(*args, **kwargs)

    @staticmethod
    def retry(*args, **kwargs):
        """Реализация повторных попыток по умолчанию: вызывает переданное исключение, чтобы сделать сбои видимыми
        В тестах этот атрибут обычно исправляется, чтобы убедиться, что повторная попытка была вызвана (например, с помощью исправления
        с side_effect=RuntimeError("повторная попытка выполнения задачи")). Указание конкретного метода
        позволяет patch.object(...) работать даже при отсутствии Celery.
        """
        exc = kwargs.get("exc") if "exc" in kwargs else (args[0] if args else None)
        if exc:
            # По умолчанию повторно генерируется исходное исключение — в тестах этот метод будет исправлен
            raise exc
        raise RuntimeError("retry called")


# --- Реализации (чисто функции) ---


def _cleanup_expired_payments_impl():
    try:
        from Payments.models import Payment  # type: ignore
    except Exception:
        logger.debug("cleanup_expired_payments: Payments.models импорт недоступен")
        return {"processed": 0}

    expired_time = _now() - timedelta(hours=24)
    expired_payments = Payment.objects.filter(
        status="pending", created_at__lt=expired_time
    )

    count = expired_payments.count()
    expired_payments.update(status="failed")

    logger.info("Помечены как неудачные %d просроченных платежей", count)
    return {"processed": count}


def _cleanup_expired_discounts_impl():
    try:
        from Payments.models import PriceConfiguration  # type: ignore
    except Exception:
        logger.debug("cleanup_expired_discounts: Payments.models импорт недоступен")
        return {"processed": 0}

    expired_configs = PriceConfiguration.objects.filter(
        discount_end_date__lt=_now(), discount_price__isnull=False
    )
    count = expired_configs.count()
    expired_configs.update(discount_price=None, discount_end_date=None)

    logger.info("Убраны скидки для %d товаров", count)
    return {"processed": count}


def _cleanup_expired_admin_keys_impl():
    try:
        from Admin.models import AdminKey  # type: ignore
    except Exception:
        logger.debug("cleanup_expired_admin_keys: Admin.models импорт недоступен")
        return {"processed": 0}

    now = _now()
    qs = AdminKey.objects.filter(
        is_active=True, expires_at__isnull=False, expires_at__lt=now
    )
    count = qs.count()
    if count == 0:
        logger.debug("cleanup_expired_admin_keys: нет просроченных ключей")
        return {"processed": 0}
    updated = qs.update(is_active=False)
    logger.info("cleanup_expired_admin_keys: деактивированные %d админ-ключи", updated)
    return {"processed": updated}


def _generate_daily_reports_impl():
    try:
        from django.conf import settings  # type: ignore
        from django.core.mail import send_mail  # type: ignore

        from Payments.models import Payment  # type: ignore
        from Users.models import User  # type: ignore
    except Exception:
        logger.debug("generate_daily_reports: необходимые модели/настройки недоступны")
        return {
            "processed_admins": 0,
            "message": "Ежедневный отчёт отправлен - нет админов",
        }

    yesterday = _now() - timedelta(days=1)
    payments_count = Payment.objects.filter(created_at__date=yesterday.date()).count()
    completed_payments = Payment.objects.filter(
        completed_at__date=yesterday.date(), status="completed"
    )
    revenue = sum((p.amount for p in completed_payments))

    admins = User.objects.filter(is_superuser=True, is_active=True)
    admin_emails = [a.email for a in admins]

    if admin_emails:
        subject = f"Ежедневный отчёт - {yesterday.strftime('%Y-%m-%d')}"
        message = (
            f"Статистика за {yesterday.strftime('%d.%m.%Y')}:\n\n"
            f"Создано платежей: {payments_count}\n"
            f"Завершено платежей: {completed_payments.count()}\n"
            f"Выручка: {revenue} ₽\n\n"
            "Хорошего дня!"
        )
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=True,
            )
        except Exception:
            logger.exception("generate_daily_reports: send_mail failed")

    # Возвращаем читабельное сообщение для тестов/мониторинга
    return {
        "processed_admins": len(admin_emails),
        "message": f"Ежедневный отчёт отправлен - {yesterday.strftime('%Y-%m-%d') if admin_emails else 'нет админов'}",
    }


def _update_user_progress_stats_impl():
    try:
        from Lessons.models import UserLessonProgress  # type: ignore
        from Users.models import User  # type: ignore
    except Exception:
        logger.debug("update_user_progress_stats: Lessons/Users импорт недоступен")
        return {"processed_students": 0}

    students = User.objects.filter(groups__name="student")
    processed = 0
    for student in students:
        completed_lessons = UserLessonProgress.objects.filter(
            user=student, is_completed=True
        ).count()
        total_watched_time = sum(
            p.watched_duration for p in UserLessonProgress.objects.filter(user=student)
        )
        logger.info(
            "Студент %s: завершил %d уроков, всего %d сек",
            student.email,
            completed_lessons,
            total_watched_time,
        )
        processed += 1

    return {"processed_students": processed}


def _send_course_reminders_impl():
    try:
        from django.conf import settings  # type: ignore
        from django.core.mail import send_mail  # type: ignore

        from Payments.models import PurchasedContent  # type: ignore
        from Users.models import User  # type: ignore
    except Exception:
        logger.debug("send_course_reminders: Users/Payments импорт недоступен")
        return {"sent": 0}

    week_ago = _now() - timedelta(days=7)
    students_to_remind = User.objects.filter(
        groups__name="student", last_login__lt=week_ago, purchased_content__isnull=False
    ).distinct()

    count = 0
    for student in students_to_remind:
        purchased = PurchasedContent.objects.filter(user=student)
        if purchased.exists():
            subject = "Не забывайте про ваши курсы!"
            titles = [
                p.discipline.title if p.discipline else p.lesson.title
                for p in purchased[:3]
            ]
            message = f"Привет, {student.first_name}!\n\nВы давно не заходили. У вас есть доступ к курсам: {', '.join(titles)}\n\nПродолжайте обучение: {settings.BASE_URL}\n"
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [student.email],
                    fail_silently=True,
                )
            except Exception:
                logger.exception(
                    "send_course_reminders: send_mail потерпел неудачу из-за %s",
                    student.email,
                )
            count += 1
    return {"sent": count}


def _process_payment_completion_impl(payment_id):
    try:
        from Payments.models import Payment  # type: ignore
        from Payments.services import PaymentService  # type: ignore
    except Exception:
        logger.debug("process_payment_completion: Payments импорт недоступен")
        return {"status": "not_found", "message": f"Платёж {payment_id} не найден."}

    try:
        payment = Payment.objects.get(id=payment_id)

        if payment.status == "pending":
            if getattr(payment, "yookassa_payment_id", None):
                try:
                    from Payments.yookassa_service import (
                        YooKassaService,
                    )  # type: ignore

                    yookassa_service = YooKassaService()
                    yookassa_payment_info = yookassa_service.get_payment_info(
                        payment.yookassa_payment_id
                    )
                    status = None
                    if isinstance(yookassa_payment_info, dict):
                        status = yookassa_payment_info.get("status")

                except Exception as e:
                    logger.exception("Ошибка запроса в YooKassa: %s", e)
                    raise

                if status == "succeeded":
                    PaymentService.complete_payment(payment.transaction_id)
                    logger.info("Платеж %s успешно завершён", payment_id)
                    return {
                        "status": "completed",
                        "message": f"Платёж {payment_id} успешно завершён.",
                    }
                elif status == "canceled":
                    payment.status = "failed"
                    payment.save()
                    logger.warning("Платеж %s отменен в ЮKassa", payment_id)
                    return {
                        "status": "failed",
                        "message": f"Платёж {payment_id} отменён.",
                    }
                elif status == "pending":
                    logger.info("Платеж %s все еще в процессе в ЮKassa", payment_id)
                    return {
                        "status": "pending",
                        "message": f"Платёж {payment_id} ещё в процессе.",
                    }
            else:
                PaymentService.complete_payment(payment.transaction_id)
                logger.info("Платеж %s успешно завершён", payment_id)
                return {
                    "status": "completed",
                    "message": f"Платёж {payment_id} успешно завершён.",
                }

        return {
            "status": "not_ready",
            "message": f"Платёж {payment_id} не готов к завершению.",
        }

    except Payment.DoesNotExist:
        logger.error("Платеж %s не найден", payment_id)
        return {"status": "not_found", "message": f"Платёж {payment_id} не найден."}


def _send_payment_success_notification_impl(payment_id):
    try:
        from django.conf import settings  # type: ignore
        from django.core.mail import send_mail  # type: ignore

        from Payments.models import Payment  # type: ignore
    except Exception:
        logger.debug(
            "send_payment_success_notification: Payments.models импорт недоступен"
        )
        return {"status": "not_found", "message": f"Платёж {payment_id} не найден."}

    try:
        payment = Payment.objects.select_related("user", "discipline", "lesson").get(
            id=payment_id
        )
        if payment.status == "completed":
            content_name = (
                payment.discipline.title if payment.discipline else payment.lesson.title
            )
            subject = f"✅ Оплата успешно завершена - {content_name}"
            message = (
                f"Здравствуйте, {payment.user.first_name}!\n\n"
                f"Ваша оплата успешно обработана:\n\n📚 Контент: {content_name}\n💰 Сумма: {payment.amount} ₽\n📅 "
                f"Дата: {payment.completed_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Перейти к обучению: {settings.BASE_URL}\n\nС наилучшими пожеланиями,\nКоманда LearningPlatform"
            )
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [payment.user.email],
                    fail_silently=True,
                )
            except Exception:
                logger.exception(
                    "send_payment_success_notification: send_mail потерпел неудачу из-за %s",
                    payment.user.email,
                )
            logger.info(
                "Уведомление об оплате отправлено пользователю %s", payment.user.email
            )
            return {
                "status": "notification_sent",
                "message": f"Уведомление отправлено по адресу {payment.user.email}",
            }
        return {"status": "not_ready", "message": f"Платёж {payment_id} не готов."}
    except Payment.DoesNotExist:
        logger.error("Платеж %s не найден", payment_id)
        return {"status": "not_found", "message": f"Платёж {payment_id} не найден."}


def _generate_payment_analytics_impl():
    try:
        from django.db.models import Count, Sum  # type: ignore

        from Payments.models import Payment, PurchasedContent  # type: ignore
    except Exception:
        logger.debug("generate_payment_analytics: Payments импорт недоступен")
        return {"stats": {}, "popular_disciplines": []}

    today = _now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    stats = {
        "today": Payment.objects.filter(
            completed_at__date=today, status="completed"
        ).aggregate(count=Count("id"), sum=Sum("amount")),
        "week": Payment.objects.filter(
            completed_at__date__gte=week_ago, status="completed"
        ).aggregate(count=Count("id"), sum=Sum("amount")),
        "month": Payment.objects.filter(
            completed_at__date__gte=month_ago, status="completed"
        ).aggregate(count=Count("id"), sum=Sum("amount")),
    }

    popular_disciplines = (
        PurchasedContent.objects.filter(
            discipline__isnull=False, purchased_at__date__gte=month_ago
        )
        .values("discipline__title")
        .annotate(purchases=Count("id"))
        .order_by("-purchases")[:5]
    )

    logger.info("Аналитика платежей сгенерирована")
    return {"stats": stats, "popular_disciplines": list(popular_disciplines)}


# --- Регистрация оболочек и дополнительных задач Celery ---

# сопоставление общедоступного имени -> функции impl и kwargs регистрации celery
_TASKS = [
    ("cleanup_expired_payments", _cleanup_expired_payments_impl, {}),
    ("cleanup_expired_discounts", _cleanup_expired_discounts_impl, {}),
    ("cleanup_expired_admin_keys", _cleanup_expired_admin_keys_impl, {}),
    ("generate_daily_reports", _generate_daily_reports_impl, {}),
    ("update_user_progress_stats", _update_user_progress_stats_impl, {}),
    ("send_course_reminders", _send_course_reminders_impl, {}),
    (
        "process_payment_completion",
        _process_payment_completion_impl,
        {
            "bind": True,
            "autoretry_for": (Exception,),
            "retry_kwargs": {"max_retries": 3, "countdown": 60},
        },
    ),
    ("send_payment_success_notification", _send_payment_success_notification_impl, {}),
    ("generate_payment_analytics", _generate_payment_analytics_impl, {}),
]

# СОздаём объект-оболочки в глобальных переменных модуля
for public_name, impl, celery_kwargs in _TASKS:
    celery_task = None
    if _shared_task is not None:
        try:
            # Для связанных задач нам нужно создать простую функцию-оболочку, которая принимает self,
            # если bind имеет значение True.
            if celery_kwargs.get("bind"):

                def _make_bound(f):
                    def _task(self, *args, **kwargs):
                        return f(*args, **kwargs)

                    return _task

                task_fn = _make_bound(impl)
            else:
                task_fn = impl

            # Подготавливаем kwargs для регистрации celery задачи и явно задаём имя
            task_kwargs = {k: v for k, v in celery_kwargs.items()}
            # Устанавливаем имя задачи таким, каким его ожидает CELERY_BEAT_SCHEDULE
            task_kwargs.setdefault("name", f"utils.celery_tasks.{public_name}")

            celery_task = _shared_task(**task_kwargs)(task_fn)
        except Exception:
            logger.debug(
                "Не удалось зарегистрировать celery задачу %s — продолжим без celery",
                public_name,
            )
            celery_task = None

    # Создаём обёртку (TaskWrapper) и выставляем её в module globals
    wrapper = TaskWrapper(impl, celery_task)
    globals()[public_name] = wrapper


__all__ = [name for name, _impl, _kw in _TASKS]

# expose aliases
cleanup_expired_payments = globals().get("cleanup_expired_payments")
cleanup_expired_discounts = globals().get("cleanup_expired_discounts")
cleanup_expired_admin_keys = globals().get("cleanup_expired_admin_keys")
generate_daily_reports = globals().get("generate_daily_reports")
update_user_progress_stats = globals().get("update_user_progress_stats")
send_course_reminders = globals().get("send_course_reminders")
process_payment_completion = globals().get("process_payment_completion")
send_payment_success_notification = globals().get("send_payment_success_notification")
generate_payment_analytics = globals().get("generate_payment_analytics")
