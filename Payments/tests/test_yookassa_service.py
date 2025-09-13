from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from Payments.yookassa_service import YooKassaService


class YooKassaServiceTests(TestCase):
    """Набор unit-тестов для YooKassaService."""

    def test_get_test_payment_data_contains_keys(self):
        data = YooKassaService.get_test_payment_data()
        # Простейшая проверка наличия ключей
        self.assertIn("test_card_number", data)
        self.assertIn("webhook_url", data)
        self.assertIn("return_url_pattern", data)

    @override_settings(YOOKASSA_TEST_MODE=True)
    def test_validate_webhook_notification_in_test_mode(self):
        # В тестовом режиме функция должна просто вернуть True
        self.assertTrue(YooKassaService.validate_webhook_notification({}, "{}"))

    @override_settings(YOOKASSA_TEST_MODE=False)
    def test_validate_webhook_notification_factory_two_args(self):
        # Мокаем фабрику, у которой create принимает (body, headers)
        class FakeFactory:
            def __init__(self):
                self.called = False

            def create(self, body, headers):
                self.called = True
                # не бросаем исключений
                return True

        with patch(
            "Payments.yookassa_service.WebhookNotificationFactory",
            return_value=FakeFactory(),
        ):
            ok = YooKassaService.validate_webhook_notification({"H": "v"}, '{"x":1}')
            self.assertTrue(ok)

    @override_settings(YOOKASSA_TEST_MODE=False)
    def test_validate_webhook_notification_factory_one_arg(self):
        # Мокаем фабрику, у которой create принимает только (body)
        class FakeFactory:
            def __init__(self):
                self.called = False

            def create(self, body):
                self.called = True
                return True

        with patch(
            "Payments.yookassa_service.WebhookNotificationFactory",
            return_value=FakeFactory(),
        ):
            ok = YooKassaService.validate_webhook_notification({}, '{"x":2}')
            self.assertTrue(ok)

    @patch("Payments.yookassa_service.Payment.create")
    def test_create_payment_success(self, mock_create):
        # Мокаем объект платежа, который возвращает SDK
        payment_obj = MagicMock()
        payment_obj.id = "p-id-123"
        payment_obj.status = "waiting_for_capture"
        conf = MagicMock()
        conf.confirmation_url = "https://pay.url/confirm"
        payment_obj.confirmation = conf
        payment_obj.created_at = "2025-01-01T00:00:00Z"
        payment_obj.metadata = {"transaction_id": "tx1"}
        mock_create.return_value = payment_obj

        res = YooKassaService.create_payment(
            amount=Decimal("10.00"), description="d", return_url="https://r"
        )
        self.assertEqual(res["payment_id"], payment_obj.id)
        self.assertEqual(
            res["confirmation_url"], payment_obj.confirmation.confirmation_url
        )

    @patch("Payments.yookassa_service.Payment.find_one")
    def test_get_payment_info_success(self, mock_find):
        obj = MagicMock()
        obj.id = "p-1"
        obj.status = "succeeded"
        amt = MagicMock()
        amt.value = "123.45"
        amt.currency = "RUB"
        obj.amount = amt
        obj.created_at = "ts"
        obj.metadata = {"transaction_id": "tx"}
        obj.paid = True
        obj.refundable = False
        mock_find.return_value = obj

        info = YooKassaService.get_payment_info("p-1")
        self.assertEqual(info["payment_id"], "p-1")
        self.assertEqual(info["amount"], Decimal("123.45"))

    @patch("Payments.yookassa_service.Payment.find_one")
    @patch("Payments.yookassa_service.Payment.capture")
    def test_confirm_payment_waiting_for_capture_triggers_capture(
        self, mock_capture, mock_find
    ):
        p = MagicMock()
        p.status = "waiting_for_capture"
        p.amount = {"value": "1.00"}
        mock_find.return_value = p

        ok = YooKassaService.confirm_payment("any")
        self.assertTrue(ok)
        mock_capture.assert_called()

    @patch("Payments.yookassa_service.Payment.find_one")
    def test_confirm_payment_other_status_returns_false(self, mock_find):
        p = MagicMock()
        p.status = "succeeded"
        mock_find.return_value = p
        self.assertFalse(YooKassaService.confirm_payment("id"))

    @patch("Payments.yookassa_service.Payment.cancel")
    def test_cancel_payment_success(self, mock_cancel):
        mock_cancel.return_value = None
        ok = YooKassaService.cancel_payment("pid")
        self.assertTrue(ok)

    @patch("Payments.yookassa_service.Refund.create")
    def test_create_refund_success(self, mock_refund_create):
        rf = MagicMock()
        rf.id = "r1"
        rf.status = "succeeded"
        amt = MagicMock()
        amt.value = "10.00"
        rf.amount = amt
        rf.created_at = "ts"
        mock_refund_create.return_value = rf

        res = YooKassaService.create_refund("p1", amount=Decimal("10.00"), reason="x")
        self.assertEqual(res["refund_id"], "r1")
        self.assertEqual(res["amount"], Decimal("10.00"))
