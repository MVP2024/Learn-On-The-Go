from unittest.mock import patch

from django.test import TestCase, override_settings

from Payments.yookassa_service import YooKassaService


class YooKassaServiceExtraTests(TestCase):
    def test_validate_in_test_mode_returns_true(self):
        with override_settings(YOOKASSA_TEST_MODE=True):
            self.assertTrue(YooKassaService.validate_webhook_notification({}, "{}"))

    def test_validate_calls_factory_with_two_args(self):
        class FakeFactory:
            def create(self, body, headers):
                self.called = (body, headers)

        with override_settings(YOOKASSA_TEST_MODE=False):
            with patch(
                "Payments.yookassa_service.WebhookNotificationFactory",
                return_value=FakeFactory(),
            ):
                ok = YooKassaService.validate_webhook_notification(
                    {"H": "v"}, '{"x":1}'
                )
                self.assertTrue(ok)

    def test_validate_calls_factory_with_one_arg_when_two_arg_signature_missing(self):
        class FakeFactory:
            def create(self, body):
                self.called = (body,)

        with override_settings(YOOKASSA_TEST_MODE=False):
            with patch(
                "Payments.yookassa_service.WebhookNotificationFactory",
                return_value=FakeFactory(),
            ):
                ok = YooKassaService.validate_webhook_notification(
                    {"H": "v"}, '{"x":2}'
                )
                self.assertTrue(ok)

    def test_validate_returns_false_if_factory_missing(self):
        with override_settings(YOOKASSA_TEST_MODE=False):
            with patch("Payments.yookassa_service.WebhookNotificationFactory", None):
                ok = YooKassaService.validate_webhook_notification(
                    {"H": "v"}, '{"x":3}'
                )
                self.assertFalse(ok)
