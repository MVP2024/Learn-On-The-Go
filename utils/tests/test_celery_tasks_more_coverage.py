import sys
import types
from unittest.mock import patch

from django.test import TestCase

import utils.celery_tasks as ct


class CeleryTasksDecoratorsAndNowTests(TestCase):
    """Покрываем вспомогательные части: импорт celery.shared_task может отсутствовать,
    а также _now() при отсутствии django.utils.timezone.
    """

    def test__now_fallback_without_django_timezone(self):
        # Удаляем модуль django.utils, чтобы импорт timezone упал и сработал fallback
        old_utils = sys.modules.get("django.utils")
        sys.modules["django.utils"] = types.ModuleType("django.utils")
        try:
            val = ct._now()
            from datetime import datetime

            self.assertIsInstance(val, datetime)
        finally:
            if old_utils is not None:
                sys.modules["django.utils"] = old_utils
            else:
                del sys.modules["django.utils"]


class CeleryTasksGenerateEmailExceptionsTests(TestCase):
    """Покрываем ветки исключений при отправке писем в generate_daily_reports и
    send_payment_success_notification.
    """

    @patch("django.core.mail.send_mail", side_effect=Exception("mail fail"))
    def test_generate_daily_reports_handles_send_mail_exception(self, _):
        # Даже при исключении функция должна вернуть словарь с processed_admins
        out = ct._generate_daily_reports_impl()
        self.assertIsInstance(out, dict)
        self.assertIn("processed_admins", out)

    @patch("django.core.mail.send_mail", side_effect=Exception("mail fail"))
    def test_send_payment_success_notification_mail_error_is_caught(self, _):
        # Создадим completed payment, чтобы пройти до send_mail и инициировать исключение
        from decimal import Decimal

        from django.contrib.auth import get_user_model
        from django.utils import timezone

        from Disciplines.models import Discipline
        from Payments.models import Payment

        User = get_user_model()
        u = User.objects.create_user(email="mail_err@a.aa", password="pw")
        d = Discipline.objects.create(title="NotifDisc", description="d")
        p = Payment.objects.create(
            user=u,
            payment_type="discipline",
            discipline=d,
            amount=Decimal("1.00"),
            status="completed",
            transaction_id="m1",
            completed_at=timezone.now(),
        )
        out = ct._send_payment_success_notification_impl(p.id)
        # Должен вернуться валидный ответ (notification_sent), несмотря на ошибку отправки
        self.assertIsInstance(out, dict)
        self.assertIn(
            out.get("status"), {"notification_sent", "not_ready", "not_found"}
        )
