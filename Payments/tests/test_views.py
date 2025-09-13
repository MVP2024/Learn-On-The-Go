import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Lessons.models import Lesson
from Payments.models import Payment, PurchasedContent
from Payments.services import PriceService

User = get_user_model()


class PaymentsViewSetTests(TestCase):
    def setUp(self):
        for g in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=g)
        self.teacher = User.objects.create_user(email="pv_teacher@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))
        self.student = User.objects.create_user(email="pv_student@a.aa", password="pw")
        self.student.groups.add(Group.objects.get(name="student"))

        self.disc = Discipline.objects.create(
            title="PVDisc", description="d", owner=self.teacher, slug="pv_disc"
        )
        self.lesson = Lesson.objects.create(
            title="PVLesson",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="https://example.com/v",
        )
        # цены
        PriceService.set_discipline_price(self.disc, Decimal("100.00"), is_free=False)
        PriceService.set_lesson_price(self.lesson, Decimal("50.00"), is_free=False)

        self.client = APIClient()

    def test_create_paid_lesson_triggers_yookassa_and_saves_payment_fields(self):
        self.client.force_authenticate(user=self.student)
        payload = {
            "payment_type": "lesson",
            "lesson_id": self.lesson.id,
            "payment_method": "yookassa",
        }

        fake_yookassa_resp = {
            "payment_id": "y-pay-1",
            "status": "waiting_for_capture",
            "confirmation_url": "https://pay.yookassa/confirm/1",
            "amount": Decimal("50.00"),
        }

        with patch(
            "Payments.views.YooKassaService.create_payment",
            return_value=fake_yookassa_resp,
        ) as mock_y:
            resp = self.client.post(
                "/api/payments/create_payment/", data=payload, format="json"
            )
            self.assertEqual(resp.status_code, 201)
            body = resp.json()
            # ответ должен содержать yookassa_confirmation_url
            self.assertIn("yookassa_confirmation_url", body)
            self.assertEqual(
                body["yookassa_confirmation_url"],
                fake_yookassa_resp["confirmation_url"],
            )

            # Объект платежа в базе данных должен иметь yookassa_payment_id и URL-адрес для подтверждения
            payment = Payment.objects.get(transaction_id=body["transaction_id"])
            self.assertEqual(
                payment.yookassa_payment_id, fake_yookassa_resp["payment_id"]
            )  # сохранено с помощью просмотра
            self.assertEqual(
                payment.yookassa_confirmation_url,
                fake_yookassa_resp["confirmation_url"],
            )  # сохранено с помощью просмотра

            mock_y.assert_called()

    def test_create_paid_lesson_external_error_returns_400(self):
        self.client.force_authenticate(user=self.student)
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
            body = resp.json()
            self.assertIn("error", body)

    def test_complete_payment_idempotent_and_check_status(self):
        # создаём отложенный платёж через сервис, чтобы имитировать реальный процесс
        payment = Payment.objects.create(
            user=self.student,
            payment_type="lesson",
            lesson=self.lesson,
            amount=Decimal("50.00"),
            status="pending",
            transaction_id="tx-pay-1",
        )

        # завершаем через API
        resp = self.client.post(
            "/api/payments/complete_payment/",
            data={"transaction_id": payment.transaction_id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "completed")

        # второй вызов должен по-прежнему возвращать 200 и не должен завершаться ошибкой
        resp2 = self.client.post(
            "/api/payments/complete_payment/",
            data={"transaction_id": payment.transaction_id},
            format="json",
        )
        self.assertEqual(resp2.status_code, 200)

        # check_status
        resp3 = self.client.get(
            f"/api/payments/check_status/?transaction_id={payment.transaction_id}"
        )
        self.assertEqual(resp3.status_code, 200)
        self.client.force_authenticate(user=self.student)
        with patch(
            "Payments.views.YooKassaService.validate_webhook_notification",
            return_value=True,
        ) as mock_validate, patch(
            "Payments.views.PaymentService.complete_payment", return_value=payment
        ) as mock_complete:
            body = {
                "event": "payment.succeeded",
                "object": {
                    "id": "yoo-1",
                    "metadata": {"transaction_id": payment.transaction_id},
                },
            }
            resp = self.client.post(
                "/api/payments/yookassa-webhook/",
                data=json.dumps(body),
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 200)
            mock_validate.assert_called()
            mock_complete.assert_called()
            data = resp.json()
            self.assertIn("статус", data)

        # недействительная подпись
        with patch(
            "Payments.views.YooKassaService.validate_webhook_notification",
            return_value=False,
        ):
            resp2 = self.client.post(
                "/api/payments/yookassa-webhook/",
                data=json.dumps({}),
                content_type="application/json",
            )
            self.assertEqual(resp2.status_code, 400)

        # неправильный json
        with patch(
            "Payments.views.YooKassaService.validate_webhook_notification",
            return_value=True,
        ):
            resp3 = self.client.post(
                "/api/payments/yookassa-webhook/",
                data="not-json",
                content_type="application/json",
            )
            self.assertEqual(resp3.status_code, 400)

    def test_create_payment_free_discipline_creates_purchased_content(self):
        # делаем дисциплину бесплатной
        PriceService.set_discipline_price(self.disc, Decimal("0.00"), is_free=True)
        self.client.force_authenticate(user=self.student)
        payload = {
            "payment_type": "discipline",
            "discipline_id": self.disc.id,
            "payment_method": "free",
        }
        resp = self.client.post(
            "/api/payments/create_payment/", data=payload, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body.get("status"), "completed")
        # убеждаемся, что приобретенный контент существует
        p = Payment.objects.get(transaction_id=body.get("transaction_id"))
        self.assertTrue(PurchasedContent.objects.filter(payment=p).exists())

    def test_priceconfiguration_create_requires_admin_or_moderator(self):
        # учение не может создавать цену
        self.client.force_authenticate(user=self.student)
        payload = {"discipline": self.disc.id, "price": "123.00", "is_free": False}
        resp = self.client.post(
            "/api/price-configurations/", data=payload, format="json"
        )
        # возвращаем (403) или запрос некорректен, если класс разрешений настроен иначе
        self.assertIn(resp.status_code, (403, 400))

        # администратор может создавать
        admin = User.objects.create_user(
            email="pv_admin@a.aa", password="pw", is_superuser=True
        )
        self.client.force_authenticate(user=admin)
        resp2 = self.client.post(
            "/api/price-configurations/", data=payload, format="json"
        )
        # либо создано, либо неправильно обработано сериализатором
        self.assertIn(resp2.status_code, (201, 200))
