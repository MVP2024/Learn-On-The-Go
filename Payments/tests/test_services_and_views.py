from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Lessons.models import Lesson
from Payments.models import Payment, PurchasedContent
from Payments.services import PaymentService, PriceService

User = get_user_model()


class PaymentsServicesViewsTests(TestCase):
    """Тесты логики платежей и связанного API поведения"""

    def setUp(self):
        for g in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=g)
        self.teacher = User.objects.create_user(email="pay_teacher@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))
        self.student = User.objects.create_user(email="pay_student@a.aa", password="pw")
        self.student.groups.add(Group.objects.get(name="student"))
        self.disc = Discipline.objects.create(
            title="PayDisc", description="d", owner=self.teacher, slug="pay_disc"
        )
        self.lesson = Lesson.objects.create(
            title="PayLesson",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="https://example.com/v",
        )
        # настроим цены
        PriceService.set_discipline_price(self.disc, Decimal("0.00"), is_free=True)
        PriceService.set_lesson_price(self.lesson, Decimal("50.00"), is_free=False)
        self.client = APIClient()

    def test_create_free_discipline_payment_auto_completed(self):
        # покупка дисциплины с ценой 0 должна сразу завершиться
        payment = PaymentService.create_payment(
            user=self.student,
            payment_type="discipline",
            discipline_id=self.disc.id,
            payment_method="free",
        )
        self.assertEqual(payment.status, "completed")
        # в PurchasedContent должно появиться
        self.assertTrue(PurchasedContent.objects.filter(payment=payment).exists())

    def test_create_paid_lesson_payment_pending(self):
        p = PaymentService.create_payment(
            user=self.student,
            payment_type="lesson",
            lesson_id=self.lesson.id,
            payment_method="yookassa",
        )
        self.assertEqual(p.status, "pending")
        self.assertEqual(p.amount, Decimal("50.00"))

    def test_complete_payment_idempotent(self):
        p = PaymentService.create_payment(
            user=self.student,
            payment_type="lesson",
            lesson_id=self.lesson.id,
            payment_method="yookassa",
        )
        pid = p.transaction_id
        PaymentService.complete_payment(pid)
        p.refresh_from_db()
        self.assertEqual(p.status, "completed")
        # повторный вызов не падает и возвращает объект
        p2 = PaymentService.complete_payment(pid)
        self.assertEqual(p2.id, p.id)

    def test_cannot_create_payment_for_missing_lesson_or_discipline(self):
        from rest_framework import serializers

        with self.assertRaises(serializers.ValidationError):
            PaymentService.create_payment(
                user=self.student, payment_type="lesson", lesson_id=99999
            )
        with self.assertRaises(serializers.ValidationError):
            PaymentService.create_payment(
                user=self.student, payment_type="discipline", discipline_id=99999
            )

    def test_has_access_helpers(self):
        # до покупки — нет доступа
        self.assertFalse(PaymentService.has_access_to_lesson(self.student, self.lesson))
        # создаём completed payment и проверяем доступ
        payment = Payment.objects.create(
            user=self.student,
            payment_type="lesson",
            lesson=self.lesson,
            amount=Decimal("50.00"),
            status="completed",
            transaction_id="tpp1",
        )
        # Используем get_or_create чтобы тест был устойчив к тому, создал ли сигнал запись автоматически
        PurchasedContent.objects.get_or_create(
            payment=payment, defaults={"user": self.student, "lesson": self.lesson}
        )
        self.assertTrue(PaymentService.has_access_to_lesson(self.student, self.lesson))

    def test_create_payment_view_flow_minimal(self):
        # проверяем, что API create_payment работает и возвращает 201 для бесплатного
        self.client.force_authenticate(user=self.student)
        resp = self.client.post(
            "/api/payments/create_payment/",
            data={
                "payment_type": "discipline",
                "discipline_id": self.disc.id,
                "payment_method": "free",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertIn("status", body)
        self.assertEqual(body.get("status"), "completed")
