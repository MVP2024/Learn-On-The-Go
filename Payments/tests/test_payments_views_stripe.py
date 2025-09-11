from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Lessons.models import Lesson
from Payments.models import Payment


class PaymentViewsStripeTests(TestCase):
    """Тесты для ветки Stripe в PaymentViewSet.create_payment и вспомогательные проверки."""

    def setUp(self):
        self.client = APIClient()
        # Создаём пользователя-студента
        User = get_user_model()
        self.user = User.objects.create_user(email="stripe_student@a.aa", password="pw")
        g, _ = Group.objects.get_or_create(name="student")
        self.user.groups.add(g)
        self.client.force_authenticate(self.user)
        # Минимальный контент
        self.discipline = Discipline.objects.create(title="D", description="d")
        self.lesson = Lesson.objects.create(
            title="L",
            discipline=self.discipline,
            owner=None,
            lesson_order=1,
            video_url="http://ex",
        )

    @patch("Payments.views.StripeService.create_payment_intent")
    @patch("Payments.views.PaymentService.create_payment")
    def test_create_payment_stripe_flow_adds_client_secret(
        self, mock_create_payment, mock_intent
    ):
        """Создание платежа с payment_method=stripe добавляет client_secret в ответ и сохраняет ID intent'а."""
        # Готовим платеж, который «создаёт» PaymentService.create_payment
        payment = Payment.objects.create(
            user=self.user,
            payment_type="lesson",
            lesson=None,
            amount=Decimal("10.00"),
            status="pending",
            transaction_id="tx-stripe-1",
        )
        mock_create_payment.return_value = payment
        mock_intent.return_value = {
            "payment_intent_id": "pi_123",
            "client_secret": "cs_test_abc",
        }

        payload = {
            "payment_type": "lesson",
            "lesson_id": self.lesson.id,
            "payment_method": "stripe",
        }
        resp = self.client.post(
            "/api/payments/create_payment/", data=payload, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("stripe_client_secret", data)
        self.assertEqual(data["stripe_client_secret"], "cs_test_abc")

        # Обновлённый платеж должен получить stripe_payment_intent_id
        payment.refresh_from_db()
        self.assertEqual(payment.stripe_payment_intent_id, "pi_123")

    def test_price_config_perform_create_permission_denied(self):
        """perform_create должен кидать PermissionDenied для не-админа/модератора/суперпользователя."""
        from rest_framework.exceptions import PermissionDenied
        from rest_framework.test import APIRequestFactory

        from Payments.views import PriceConfigurationViewSet

        factory = APIRequestFactory()
        request = factory.post("/api/price-configurations/", data={})
        request.user = self.user  # обычный студент

        viewset = PriceConfigurationViewSet()
        viewset.request = request

        class DummySerializer:
            def save(self):
                pass

        with self.assertRaises(PermissionDenied):
            viewset.perform_create(DummySerializer())
