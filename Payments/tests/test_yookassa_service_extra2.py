from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from Payments.yookassa_service import YooKassaService


class YooKassaServiceMoreTests(TestCase):
    def test_get_test_payment_data_keys(self):
        data = YooKassaService.get_test_payment_data()
        self.assertIn("test_card_number", data)
        self.assertIn("webhook_url", data)

    @override_settings(YOOKASSA_TEST_MODE=False)
    def test_validate_webhook_factory_none_returns_false(self):
        # Функция Ensure возвращает False, если  factory недоступен
        with patch("Payments.yookassa_service.WebhookNotificationFactory", None):
            ok = YooKassaService.validate_webhook_notification({"H": "v"}, "{}")
            self.assertFalse(ok)

    @patch("Payments.yookassa_service.Payment.create")
    def test_create_payment_returns_expected_structure(self, mock_create):
        payment_obj = MagicMock()
        payment_obj.id = "p-1"
        payment_obj.status = "waiting_for_capture"
        conf = MagicMock()
        conf.confirmation_url = "https://pay.url/confirm"
        payment_obj.confirmation = conf
        payment_obj.created_at = "ts"
        payment_obj.metadata = {"transaction_id": "tx1"}
        mock_create.return_value = payment_obj

        res = YooKassaService.create_payment(
            amount=Decimal("10.00"), description="d", return_url="https://r"
        )
        self.assertEqual(res["payment_id"], "p-1")
        self.assertIn("confirmation_url", res)

    @patch("Payments.yookassa_service.Payment.find_one")
    def test_get_payment_info_parses(self, mock_find):
        obj = MagicMock()
        obj.id = "pid"
        obj.status = "succeeded"
        amt = MagicMock()
        amt.value = "12.34"
        amt.currency = "RUB"
        obj.amount = amt
        obj.created_at = "ts"
        obj.metadata = {}
        obj.paid = True
        obj.refundable = False
        mock_find.return_value = obj
        info = YooKassaService.get_payment_info("pid")
        self.assertEqual(info["payment_id"], "pid")
        self.assertEqual(info["amount"], Decimal("12.34"))

    @patch("Payments.yookassa_service.Payment.find_one")
    @patch("Payments.yookassa_service.Payment.capture")
    def test_confirm_waiting_for_capture_calls_capture(self, mock_capture, mock_find):
        p = MagicMock()
        p.status = "waiting_for_capture"
        p.amount = MagicMock()
        mock_find.return_value = p
        ok = YooKassaService.confirm_payment("any")
        self.assertTrue(ok)
        mock_capture.assert_called()

    @patch("Payments.yookassa_service.Refund.create")
    def test_create_refund_calls_refund(self, mock_refund):
        rf = MagicMock()
        rf.id = "r1"
        rf.status = "succeeded"
        amt = MagicMock()
        amt.value = "5.00"
        rf.amount = amt
        rf.created_at = "t"
        mock_refund.return_value = rf
        res = YooKassaService.create_refund("p1", amount=Decimal("5.00"), reason="x")
        self.assertEqual(res["refund_id"], "r1")
        self.assertEqual(res["amount"], Decimal("5.00"))

    @patch("Payments.yookassa_service.Payment.cancel")
    def test_cancel_payment_true_when_no_exception(self, mock_cancel):
        mock_cancel.return_value = None
        ok = YooKassaService.cancel_payment("pid")
        self.assertTrue(ok)
