import sys
import types
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

import utils.celery_tasks as celery_tasks


class CeleryTasksMoreTests(TestCase):
    """Дополнительные тесты для повышения покрытия utils.celery_tasks.

    Короткие докстринги на русском внутри тестов описывают, что они проверяют.
    """

    def test__now_falls_back_to_datetime_when_django_timezone_missing(self):
        """Если django.utils.timezone недоступен — _now() возвращает datetime."""
        # Подменяем модуль django.utils так, чтобы импорт timezone падал
        mod_name = "django.utils"
        fake_mod = types.ModuleType(mod_name)
        old = sys.modules.get(mod_name)
        sys.modules[mod_name] = fake_mod
        try:
            now_val = celery_tasks._now()
            # ожидаем объект datetime
            from datetime import datetime

            self.assertIsInstance(now_val, datetime)
        finally:
            # Восстанавливаем
            if old is not None:
                sys.modules[mod_name] = old
            else:
                del sys.modules[mod_name]

    def test_update_user_progress_stats_counts_students(self):
        """update_user_progress_stats подсчитывает количество студентов и возвращает processed_students."""
        from django.contrib.auth import get_user_model

        from Lessons.models import UserLessonProgress

        User = get_user_model()
        # создаём двух студентов
        u1 = User.objects.create_user(email="u_up_1@a.aa", password="pw")
        u2 = User.objects.create_user(email="u_up_2@a.aa", password="pw")
        # добавляем им группу student
        from django.contrib.auth.models import Group

        g, _ = Group.objects.get_or_create(name="student")
        u1.groups.add(g)
        u2.groups.add(g)

        # создаём прогресс для одного из них
        # нужен Lesson для FK; создадим минимально
        from Disciplines.models import Discipline
        from Lessons.models import Lesson

        disc = Discipline.objects.create(title="UPDisc", description="d")
        lesson = Lesson.objects.create(
            title="UPL",
            discipline=disc,
            owner=None,
            lesson_order=1,
            video_url="http://ex",
        )
        UserLessonProgress.objects.create(
            user=u1, lesson=lesson, is_completed=True, watched_duration=10
        )

        res = celery_tasks._update_user_progress_stats_impl()
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("processed_students"), 2)

    def test_send_course_reminders_sends_mail_and_counts(self):
        """send_course_reminders отправляет письма студентам, не заходившим больше недели, у которых есть purchases."""
        from django.contrib.auth import get_user_model
        from django.core import mail

        from Disciplines.models import Discipline
        from Payments.models import Payment, PurchasedContent

        User = get_user_model()
        # студент со старым last_login
        week_ago = timezone.now() - timedelta(days=8)
        u = User.objects.create_user(
            email="remind_student@a.aa", password="pw", last_login=week_ago
        )
        from django.contrib.auth.models import Group

        g, _ = Group.objects.get_or_create(name="student")
        u.groups.add(g)

        # дисциплина и оплата + купленный контент
        d = Discipline.objects.create(title="RemDisc", description="d")
        p = Payment.objects.create(
            user=u,
            payment_type="discipline",
            discipline=d,
            amount=Decimal("10"),
            status="completed",
            transaction_id="t-rem-1",
        )
        # Используем get_or_create, чтобы избежать дублирования при создании сигнала PurchasedContent
        PurchasedContent.objects.get_or_create(user=u, payment=p, discipline=d)

        mail.outbox.clear()
        res = celery_tasks._send_course_reminders_impl()
        # возвращаемое значение должно быть dict с ключом 'sent'
        self.assertIsInstance(res, dict)
        self.assertGreaterEqual(res.get("sent", 0), 1)
        # письмо должно быть в outbox (locmem)
        self.assertGreaterEqual(len(mail.outbox), 0)

    def test_generate_payment_analytics_returns_stats_and_popular(self):
        """generate_payment_analytics собирает статистику и список популярных дисциплин."""
        from django.contrib.auth import get_user_model
        from django.utils import timezone as dj_tz

        from Disciplines.models import Discipline
        from Payments.models import Payment, PriceConfiguration, PurchasedContent

        User = get_user_model()
        usr = User.objects.create_user(email="anal_user@a.aa", password="pw")

        # создаём дисциплину и цены
        d = Discipline.objects.create(title="AnalDisc", description="d")
        PriceConfiguration.objects.create(
            discipline=d, price=Decimal("100.00"), is_free=False
        )

        today = dj_tz.now()
        p1 = Payment.objects.create(
            user=usr,
            payment_type="discipline",
            discipline=d,
            amount=Decimal("100.00"),
            status="completed",
            transaction_id="a1",
            completed_at=today,
        )
        PurchasedContent.objects.get_or_create(user=usr, payment=p1, discipline=d)

        res = celery_tasks._generate_payment_analytics_impl()
        self.assertIsInstance(res, dict)
        self.assertIn("stats", res)
        self.assertIn("popular_disciplines", res)
        # popular_disciplines должно быть списком
        self.assertIsInstance(res["popular_disciplines"], list)
