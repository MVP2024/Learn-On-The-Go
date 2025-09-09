from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Lessons.models import Lesson
from Payments.services import PriceService
from Users.models import User


class PaymentsViewsExtraTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="pvx_student@a.aa", password="pw")
        self.user.groups.create(name="student")
        self.client.force_authenticate(user=self.user)
        self.teacher = User.objects.create_user(email="pvx_teacher@a.aa", password="pw")
        disc = Discipline.objects.create(
            title="PVX", description="d", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="PVX L",
            discipline=disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="http://ex",
        )
        # убеждаемся, что цена за урок указана, чтобы PaymentService.create_payment не выдавал ошибку
        PriceService.set_lesson_price(self.lesson, Decimal("50.00"), is_free=False)

    def test_create_payment_yookassa_remote_error_returns_400(self):
        payload = {
            "payment_type": "lesson",
            "lesson_id": self.lesson.id,
            "payment_method": "yookassa",
        }
        with patch(
            "Payments.views.YooKassaService.create_payment",
            side_effect=Exception("remote fail"),
        ):
            resp = self.client.post(
                "/api/payments/create_payment/", data=payload, format="json"
            )
            self.assertEqual(resp.status_code, 400)
            self.assertIn("error", resp.json())

    def test_create_payment_yookassa_success_saves_payment_fields(self):
        fake = {
            "payment_id": "py-1",
            "status": "waiting_for_capture",
            "confirmation_url": "https://pay.url/confirm",
            "amount": Decimal("50"),
        }
        payload = {
            "payment_type": "lesson",
            "lesson_id": self.lesson.id,
            "payment_method": "yookassa",
        }
        with patch("Payments.views.YooKassaService.create_payment", return_value=fake):
            resp = self.client.post(
                "/api/payments/create_payment/", data=payload, format="json"
            )
            self.assertEqual(resp.status_code, 201)
            data = resp.json()
            self.assertIn("yookassa_confirmation_url", data)
            self.assertEqual(
                data["yookassa_confirmation_url"], fake["confirmation_url"]
            )
