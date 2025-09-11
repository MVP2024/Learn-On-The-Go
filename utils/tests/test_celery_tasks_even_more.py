import sys
import types
from unittest.mock import patch

from django.test import TestCase

import utils.celery_tasks as ct


class CeleryTasksEvenMoreTests(TestCase):
    """Дополнительные тесты для увеличения покрытия utils.celery_tasks."""

    def test_generate_payment_analytics_import_fail_returns_empty(self):
        """Если импорт моделей Payments падает — функция возвращает пустые структуры."""
        mod_name = "Payments.models"
        fake_mod = types.ModuleType(mod_name)

        def __getattr__(name):  # noqa: N807 (для совместимости со style)
            raise ImportError("simulated import failure")

        fake_mod.__getattr__ = __getattr__
        old = sys.modules.get(mod_name)
        sys.modules[mod_name] = fake_mod
        try:
            res = ct._generate_payment_analytics_impl()
            self.assertEqual(res, {"stats": {}, "popular_disciplines": []})
        finally:
            if old is not None:
                sys.modules[mod_name] = old
            else:
                del sys.modules[mod_name]

    def test_process_payment_completion_without_yookassa_calls_complete(self):
        """Когда у платежа нет yookassa_payment_id, вызывается PaymentService.complete_payment."""
        from decimal import Decimal

        from django.contrib.auth import get_user_model

        from Payments.models import Payment

        User = get_user_model()
        u = User.objects.create_user(email="pc_no_yoo@a.aa", password="pw")
        p = Payment.objects.create(
            user=u,
            payment_type="discipline",
            amount=Decimal("10.00"),
            status="pending",
            transaction_id="tx-no-yoo-1",
        )

        with patch(
            "Payments.services.PaymentService.complete_payment", return_value=None
        ) as mock_complete:
            out = ct._process_payment_completion_impl(p.id)
            mock_complete.assert_called_once_with("tx-no-yoo-1")
            self.assertIsInstance(out, dict)
            self.assertEqual(out.get("status"), "completed")
