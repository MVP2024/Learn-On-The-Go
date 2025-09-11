from importlib import import_module

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from Admin.models import AdminKey


class PaymentsViewsAdminKeySmokeTests(TestCase):
    """Импорт модуля Admin.views и базовая проверка наличия AdminKeyViewSet.

    Этот тест прогружает декораторы (extend_schema/examples), чтобы покрыть
    строки вверху файла.
    """

    def test_import_payments_views_exposes_adminkey_viewset(self):
        mod = import_module("Admin.views")
        self.assertTrue(hasattr(mod, "AdminKeyViewSet"))


class PaymentsViewsAdminKeyRegenerateTests(TestCase):
    """Проверяем ветку regenerate, когда у ключа нет email и пользователя."""

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_regenerate_returns_400_when_no_email(self):
        # Ключ без пользователя и email
        ak = AdminKey.objects.create(user=None, key="no-email-key", email=None, is_active=True)

        mod = import_module("Admin.views")
        view = mod.AdminKeyViewSet()
        # Подменяем get_object, чтобы вернуть наш AdminKey
        view.get_object = lambda: ak

        req = self.factory.post("/api/adminkeys/1/regenerate/")
        # Вызов напрямую метода action
        resp = view.regenerate(req, pk=str(ak.pk))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Нет email", str(resp.data.get("detail", "")))
