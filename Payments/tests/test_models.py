from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from Disciplines.models import Discipline
from Lessons.models import Lesson
from Payments.models import Payment, PriceConfiguration, PurchasedContent

User = get_user_model()


class PaymentsModelsTests(TestCase):
    """Тесты для моделей Payments."""

    def setUp(self):
        self.user = User.objects.create_user(email="pm_user@a.aa", password="pw")
        self.teacher = User.objects.create_user(email="pm_teacher@a.aa", password="pw")
        self.disc = Discipline.objects.create(
            title="PMDisc", description="d", owner=self.teacher, slug="pm_disc"
        )
        self.lesson = Lesson.objects.create(
            title="PMLesson",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="https://example.com/v",
        )

    def test_priceconfiguration_current_price_and_str(self):
        pc = PriceConfiguration.objects.create(
            discipline=self.disc, price=Decimal("100.00"), is_free=False
        )
        self.assertIn("Цена для дисциплины", str(pc))
        self.assertEqual(pc.get_current_price(), Decimal("100.00"))
        # скидка
        pc.discount_price = Decimal("50.00")
        from datetime import timedelta

        from django.utils import timezone

        pc.discount_end_date = timezone.now() + timedelta(days=1)
        pc.save()
        self.assertEqual(pc.get_current_price(), Decimal("50.00"))

    def test_payment_str_and_clean(self):
        p = Payment.objects.create(
            user=self.user,
            payment_type="lesson",
            lesson=self.lesson,
            amount=Decimal("10.00"),
            status="pending",
            transaction_id="tx1",
        )
        self.assertIn("Платеж", str(p))
        # Чистая проверка: при неправильном построении должно возникать
        # сообщение об отсутствии урока для данного типа урока
        bad = Payment(user=self.user, payment_type="lesson", amount=Decimal("5.00"))
        with self.assertRaises(Exception):
            bad.clean()

    def test_purchased_content_unique_and_str(self):
        p = Payment.objects.create(
            user=self.user,
            payment_type="lesson",
            lesson=self.lesson,
            amount=Decimal("10.00"),
            status="completed",
            transaction_id="tx2",
        )
        pc, created = PurchasedContent.objects.get_or_create(
            payment=p, defaults={"user": self.user, "lesson": self.lesson}
        )
        self.assertFalse(created)
        self.assertIn(self.user.email, str(pc))
        # повторное создание PurchasedContent для того же user+lesson должно приводить к IntegrityError via unique_together
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            PurchasedContent.objects.create(
                user=self.user,
                lesson=self.lesson,
                payment=Payment.objects.create(
                    user=self.user,
                    payment_type="lesson",
                    lesson=self.lesson,
                    amount=Decimal("10.00"),
                    status="completed",
                    transaction_id="tx3",
                ),
            )
