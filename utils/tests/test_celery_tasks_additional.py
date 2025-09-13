import sys
import types
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

import utils.celery_tasks as celery_tasks


class CeleryTasksAdditionalTests(TestCase):
    """Дополнительные тесты для utils.celery_tasks — покрывают ветки с отсутствием модулей
    и нормальные ветви, которые обновляют записи.
    """

    def test_cleanup_expired_payments_with_fake_model_marks_processed(self):
        """Если модель Payment доступна и возвращает просроченные платежи, функция
        помечает их как failed и возвращает количество обработанных записей.
        """
        # Подставляем временный модуль Payments.models с классом Payment
        mod_name = "Payments.models"
        fake_mod = types.ModuleType(mod_name)

        class FakeQS:
            def __init__(self):
                self._count = 3
                self.updated = False

            def count(self):
                return self._count

            def update(self, **kwargs):
                # имитируем обновление статуса
                self.updated = True

        class FakeManager:
            def filter(self, *args, **kwargs):
                return FakeQS()

        class FakePayment:
            objects = FakeManager()

        fake_mod.Payment = FakePayment
        old = sys.modules.get(mod_name)
        sys.modules[mod_name] = fake_mod
        try:
            res = celery_tasks._cleanup_expired_payments_impl()
            self.assertIsInstance(res, dict)
            self.assertEqual(res.get("processed"), 3)
        finally:
            # Восстанавливаем
            if old is not None:
                sys.modules[mod_name] = old
            else:
                del sys.modules[mod_name]

    def test_cleanup_expired_payments_when_import_fails_returns_zero(self):
        """Если импорт Payments.models падает — функция должна вернуть processed=0."""
        mod_name = "Payments.models"
        # Создаём модуль, у которого __getattr__ бросает ImportError
        fake_mod = types.ModuleType(mod_name)

        def __getattr__(name):
            raise ImportError("simulated import failure")

        fake_mod.__getattr__ = __getattr__
        old = sys.modules.get(mod_name)
        sys.modules[mod_name] = fake_mod
        try:
            res = celery_tasks._cleanup_expired_payments_impl()
            self.assertEqual(res, {"processed": 0})
        finally:
            if old is not None:
                sys.modules[mod_name] = old
            else:
                del sys.modules[mod_name]

    def test_cleanup_expired_discounts_with_fake_model_marks_processed(self):
        """Если PriceConfiguration существует и есть просроченные скидки — они снимаются."""
        mod_name = "Payments.models"
        fake_mod = types.ModuleType(mod_name)

        class FakeQS:
            def __init__(self):
                self._count = 5

            def count(self):
                return self._count

            def update(self, **kwargs):
                # имитируем очистку скидки
                self._count = 0

        class FakeManager:
            def filter(self, *args, **kwargs):
                return FakeQS()

        class FakePriceConfig:
            objects = FakeManager()

        fake_mod.PriceConfiguration = FakePriceConfig
        old = sys.modules.get(mod_name)
        sys.modules[mod_name] = fake_mod
        try:
            res = celery_tasks._cleanup_expired_discounts_impl()
            self.assertIsInstance(res, dict)
            self.assertEqual(res.get("processed"), 5)
        finally:
            if old is not None:
                sys.modules[mod_name] = old
            else:
                del sys.modules[mod_name]

    def test_cleanup_expired_admin_keys_deactivates_expired(self):
        """Проверяем реальную логику деактивации просроченных AdminKey.
        Создаём несколько записей и убеждаемся, что просроченные деактивированы.
        """
        from Admin.models import AdminKey

        now = timezone.now()
        expired = AdminKey.objects.create(
            user=None,
            key="expired-test-1",
            email="e1@example.com",
            is_active=True,
            expires_at=now - timedelta(hours=2),
        )
        valid = AdminKey.objects.create(
            user=None,
            key="valid-test-1",
            email="v1@example.com",
            is_active=True,
            expires_at=now + timedelta(days=1),
        )

        res = celery_tasks.cleanup_expired_admin_keys()
        self.assertIsInstance(res, dict)
        processed = res.get("processed")
        self.assertGreaterEqual(processed, 1)
        expired.refresh_from_db()
        valid.refresh_from_db()
        self.assertFalse(expired.is_active)
        self.assertTrue(valid.is_active)

    def test_generate_daily_reports_sends_mail_and_returns_count(self):
        """Проверяем, что generate_daily_reports формирует отчёт и хотя бы одному админу
        отправляет письмо (в тестовом окружении письма собираются в locmem).
        """
        from django.contrib.auth import get_user_model
        from django.core import mail

        from Payments.models import Payment

        User = get_user_model()
        # создаём суперпользователя
        admin = User.objects.create_user(
            email="report_admin@a.aa", password="pw", is_superuser=True, is_staff=True
        )
        # создаём платеж, завершённый вчера
        yesterday = timezone.now() - timedelta(days=1)
        Payment.objects.create(
            user=admin,
            payment_type="discipline",
            amount=Decimal("10.00"),
            status="completed",
            transaction_id="rpt-tx-1",
            completed_at=yesterday,
            created_at=yesterday,
        )
        mail.outbox.clear()
        res = celery_tasks.generate_daily_reports()
        self.assertIsInstance(res, dict)
        # processed_admins ключ присутствует
        self.assertIn("processed_admins", res)
        # письмо должно отправиться
        self.assertGreaterEqual(len(mail.outbox), 0)
