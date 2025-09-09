from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from Disciplines.models import Discipline
from Lessons.models import Lesson
from Payments.models import PurchasedContent
from Payments.services import PaymentService, PriceService

User = get_user_model()


class PaymentServiceExtraTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="svc_user@a.aa", password="pw")
        self.teacher = User.objects.create_user(email="svc_teacher@a.aa", password="pw")
        self.disc = Discipline.objects.create(
            title="SvcDisc", description="d", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="SvcLesson",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="http://ex",
        )

    def test_create_payment_raises_when_price_missing(self):
        # нет PriceConfiguration -> должен raise ValidationError
        with self.assertRaises(Exception):
            PaymentService.create_payment(
                user=self.user, payment_type="lesson", lesson_id=self.lesson.id
            )

    def test_create_and_complete_free_discipline(self):
        PriceService.set_discipline_price(self.disc, Decimal("0.00"), is_free=True)
        p = PaymentService.create_payment(
            user=self.user,
            payment_type="discipline",
            discipline_id=self.disc.id,
            payment_method="free",
        )
        self.assertEqual(p.status, "completed")
        self.assertTrue(PurchasedContent.objects.filter(payment=p).exists())

    def test_create_pending_paid_lesson_and_complete(self):
        PriceService.set_lesson_price(self.lesson, Decimal("30.00"), is_free=False)
        p = PaymentService.create_payment(
            user=self.user,
            payment_type="lesson",
            lesson_id=self.lesson.id,
            payment_method="yookassa",
        )
        self.assertEqual(p.status, "pending")
        completed = PaymentService.complete_payment(p.transaction_id)
        self.assertEqual(completed.status, "completed")
        self.assertTrue(PurchasedContent.objects.filter(payment=completed).exists())

    def test_has_access_checks_lesson_and_discipline(self):
        # установочная цена и завершенный платеж
        PriceService.set_lesson_price(self.lesson, Decimal("20.00"), is_free=False)
        p = PaymentService.create_payment(
            user=self.user,
            payment_type="lesson",
            lesson_id=self.lesson.id,
            payment_method="yookassa",
        )
        PaymentService.complete_payment(p.transaction_id)
        self.assertTrue(PaymentService.has_access_to_lesson(self.user, self.lesson))
        self.assertFalse(PaymentService.has_access_to_discipline(self.user, self.disc))

    def test_complete_payment_raises_for_missing(self):
        with self.assertRaises(Exception):
            PaymentService.complete_payment("no-such")
