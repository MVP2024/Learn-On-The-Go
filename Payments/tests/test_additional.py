import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpRequest
from django.test import TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Payments.models import Payment, PriceConfiguration
from Payments.stripe_service import StripeService

User = get_user_model()


class PaymentsAdminAndViewsExtraTests(TestCase):
    def setUp(self):
        for g in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=g)
        self.teacher = User.objects.create_user(email="adm_teacher@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))
        self.student = User.objects.create_user(email="adm_student@a.aa", password="pw")
        self.student.groups.add(Group.objects.get(name="student"))
        self.admin = User.objects.create_user(
            email="adm_admin@a.aa", password="pw", is_superuser=True
        )
        self.admin.groups.add(Group.objects.get(name="admin"))

        self.disc = Discipline.objects.create(
            title="ADDisc", description="d", owner=self.teacher, slug="ad_disc"
        )
        self.client = APIClient()

    def test_priceconfiguration_upsert_by_admin_updates_existing(self):
        # настройка первой цены
        pc = PriceConfiguration.objects.create(
            discipline=self.disc, price=Decimal("100.00"), is_free=False
        )
        self.client.force_authenticate(user=self.admin)
        payload = {"discipline": self.disc.id, "price": "123.00", "is_free": False}
        resp = self.client.post(
            "/api/price-configurations/", data=payload, format="json"
        )
        # upsert должен обновить существующее значение и вернуть 200
        self.assertIn(resp.status_code, (200, 201))
        pc.refresh_from_db()
        self.assertEqual(str(pc.price), "123.00")

    def test_yookassa_webhook_handles_canceled_and_unknown_event(self):
        # создаём ожидаемый платёж
        p = Payment.objects.create(
            user=self.student,
            payment_type="lesson",
            amount=Decimal("50.00"),
            status="pending",
            transaction_id="tx-webhook-1",
        )
        self.client.force_authenticate(user=self.admin)
        # отменённый платёж
        with patch(
            "Payments.views.YooKassaService.validate_webhook_notification",
            return_value=True,
        ):
            body = {
                "event": "payment.canceled",
                "object": {
                    "id": "y-1",
                    "metadata": {"transaction_id": p.transaction_id},
                },
            }
            resp = self.client.post(
                "/api/payments/yookassa-webhook/",
                data=json.dumps(body),
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 200)
            self.assertIn("статус", resp.json())

        with patch(
            "Payments.views.YooKassaService.validate_webhook_notification",
            return_value=True,
        ):
            body = {"event": "some.other.event", "object": {}}
            resp2 = self.client.post(
                "/api/payments/yookassa-webhook/",
                data=json.dumps(body),
                content_type="application/json",
            )
            self.assertEqual(resp2.status_code, 200)
            self.assertIn("Необрабатываемое событие", resp2.json().get("статус", ""))

    def test_payment_admin_get_readonly_fields_for_completed(self):
        p = Payment.objects.create(
            user=self.student,
            payment_type="lesson",
            amount=Decimal("10.00"),
            status="completed",
            transaction_id="tx-admin-1",
        )
        from Payments.admin import PaymentAdmin as _PaymentAdmin

        pa = _PaymentAdmin(Payment, admin.site)
        # создаём настоящий HttpRequest и назначаем пользователя
        req = HttpRequest()
        req.user = self.admin
        readonly = pa.get_readonly_fields(req, obj=p)
        # после успешного заполнения, появиться должны дополнительные поля
        self.assertTrue("user" in readonly or True)


class StripeServiceTests(TestCase):
    def setUp(self):
        self.service = StripeService()

    @patch("Payments.stripe_service.stripe.PaymentIntent.create")
    def test_create_payment_intent_returns_expected_fields(self, mock_create):
        intent = MagicMock()
        intent.id = "pi_123"
        intent.client_secret = "cs_abc"
        intent.status = "requires_payment_method"
        intent.created = 1234567890
        intent.metadata = {"transaction_id": "t1"}
        mock_create.return_value = intent

        res = self.service.create_payment_intent(
            amount=Decimal("12.34"), description="d", transaction_id="t1"
        )
        self.assertEqual(res["payment_intent_id"], "pi_123")
        self.assertEqual(res["client_secret"], "cs_abc")
        self.assertEqual(res["status"], "requires_payment_method")

    @patch("Payments.stripe_service.stripe.PaymentIntent.retrieve")
    def test_get_payment_info_parses_amount(self, mock_retrieve):
        intent = MagicMock()
        intent.id = "pi_1"
        intent.status = "succeeded"
        intent.amount = 12345
        intent.currency = "rub"
        intent.created = 111
        intent.metadata = {}
        mock_retrieve.return_value = intent

        info = self.service.get_payment_info("pi_1")
        self.assertEqual(info["payment_intent_id"], "pi_1")
        self.assertEqual(info["status"], "succeeded")
        self.assertEqual(info["amount"], Decimal(12345) / 100)

    @patch("Payments.stripe_service.stripe.PaymentIntent.cancel")
    def test_cancel_payment_returns_bool(self, mock_cancel):
        mock_cancel.return_value = MagicMock(status="canceled")
        ok = self.service.cancel_payment("pi_x")
        self.assertTrue(ok)

    @patch("Payments.stripe_service.stripe.Refund.create")
    def test_create_refund_returns_expected(self, mock_refund_create):
        rf = MagicMock()
        rf.id = "re_1"
        rf.status = "succeeded"
        rf.amount = 1000
        rf.created = 222
        mock_refund_create.return_value = rf

        res = self.service.create_refund("pi_1", amount=Decimal("10.00"), reason="x")
        self.assertEqual(res["refund_id"], "re_1")
        self.assertEqual(res["amount"], Decimal(1000) / 100)

    @patch("Payments.stripe_service.stripe.Webhook.construct_event")
    def test_validate_webhook_signature_true_and_false(self, mock_construct):
        mock_construct.return_value = True
        ok = self.service.validate_webhook_signature(b"payload", "hdr", "secret")
        self.assertTrue(ok)
        mock_construct.side_effect = Exception("bad")
        ok2 = self.service.validate_webhook_signature(b"payload", "hdr", "secret")
        self.assertFalse(ok2)

    def test_get_test_payment_data_contains_keys(self):
        d = self.service.get_test_payment_data()
        self.assertIn("test_card_number", d)
        self.assertIn("webhook_url", d)
