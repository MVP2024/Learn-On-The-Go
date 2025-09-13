from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from Admin.models import AdminKey
from utils.celery_tasks import cleanup_expired_admin_keys


class AdminKeyCleanupTests(TestCase):
    """
    Небольшой тест для автоматической деактивации админ-ключей по полю expires_at.

    - создаём ключи: один просроченный, один ещё действующий
    - запускаем задачу cleanup_expired_admin_keys
    - проверяем, что просроченный ключ деактивирован, а действующий остался активным
    """

    def test_cleanup_deactivates_only_expired_keys(self):
        now = timezone.now()
        # ключ, срок действия которого прошёл
        expired = AdminKey.objects.create(
            user=None,
            key="expired-key-xyz",
            email="expired@example.com",
            is_active=True,
            expires_at=now - timedelta(hours=1),
        )

        # ключ ещё действителен
        valid = AdminKey.objects.create(
            user=None,
            key="valid-key-abc",
            email="valid@example.com",
            is_active=True,
            expires_at=now + timedelta(days=1),
        )

        # Дополнительный ключ без expires_at — не должен деактивироваться
        noexp = AdminKey.objects.create(
            user=None,
            key="noexp-key-000",
            email="noexp@example.com",
            is_active=True,
            expires_at=None,
        )

        result = cleanup_expired_admin_keys()

        # задача возвращает словарь с количеством обработанных записей
        processed = result.get("processed") if isinstance(result, dict) else None
        self.assertIsNotNone(processed)
        self.assertGreaterEqual(processed, 1)

        expired.refresh_from_db()
        valid.refresh_from_db()
        noexp.refresh_from_db()

        # Просроченный ключ должен быть деактивирован
        self.assertFalse(expired.is_active)
        # Действующий ключ остаётся активным
        self.assertTrue(valid.is_active)
        # Ключ без expires_at остаётся активным
        self.assertTrue(noexp.is_active)
