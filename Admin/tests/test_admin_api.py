from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from Admin.models import AdminKey
from Users.models import User


class AdminKeyAPITests(TestCase):
    """Тесты API для управления AdminKey (AdminKeyViewSet).

    Покрываются следующие эндпоинты:
    - list (+ фильтры is_active/email/user)
    - retrieve
    - revoke / reactivate
    - regenerate
    - resend
    - pending_requests / approve_request
    """

    def setUp(self):
        UserModel = get_user_model()
        # суперпользователь (is_staff требуется для IsAdminUser)
        self.admin = UserModel.objects.create_user(
            email="api_admin@a.aa", password="pw", is_superuser=True, is_staff=True
        )
        # обычный пользователь
        self.user = UserModel.objects.create_user(email="regular@a.aa", password="pw")
        self.client: APIClient = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_list_and_filters(self):
        ak1 = AdminKey.objects.create(
            user=self.user, key="ak-list-1", email=self.user.email, is_active=True
        )
        ak2 = AdminKey.objects.create(
            user=None, key="ak-list-2", email="other@x.y", is_active=False
        )

        resp_all = self.client.get("/api/adminkeys/")
        self.assertEqual(resp_all.status_code, 200)
        data = resp_all.json()
        # results when paginated, or list directly — handle both
        items = data.get("results", data)
        ids = {item.get("id") for item in items}
        self.assertIn(ak1.id, ids)
        self.assertIn(ak2.id, ids)

        resp_active = self.client.get("/api/adminkeys/?is_active=true")
        self.assertEqual(resp_active.status_code, 200)
        items_active = resp_active.json().get("results", resp_active.json())
        self.assertTrue(any(i.get("id") == ak1.id for i in items_active))
        self.assertFalse(any(i.get("id") == ak2.id for i in items_active))

        resp_email = self.client.get(f"/api/adminkeys/?email=other@x.y")
        self.assertEqual(resp_email.status_code, 200)
        items_email = resp_email.json().get("results", resp_email.json())
        self.assertTrue(any(i.get("id") == ak2.id for i in items_email))

    def test_revoke_and_reactivate(self):
        ak = AdminKey.objects.create(
            user=self.user, key="ak-rev", email=self.user.email, is_active=True
        )
        resp = self.client.post(f"/api/adminkeys/{ak.id}/revoke/")
        self.assertEqual(resp.status_code, 200)
        ak.refresh_from_db()
        self.assertFalse(ak.is_active)

        resp2 = self.client.post(f"/api/adminkeys/{ak.id}/reactivate/")
        self.assertEqual(resp2.status_code, 200)
        ak.refresh_from_db()
        self.assertTrue(ak.is_active)

    def test_resend_without_email_returns_400(self):
        ak = AdminKey.objects.create(user=None, key="ak-no-email", email=None)
        resp = self.client.post(f"/api/adminkeys/{ak.id}/resend/")
        self.assertEqual(resp.status_code, 400)

    @patch("Users.tasks.send_admin_key_email.delay")
    def test_regenerate_deactivates_old_and_creates_new(self, mock_send):
        ak = AdminKey.objects.create(
            user=self.user, key="ak-old", email=self.user.email, is_active=True
        )
        resp = self.client.post(f"/api/adminkeys/{ak.id}/regenerate/")
        self.assertEqual(resp.status_code, 201)
        json_data = resp.json()
        # новый ключ должен присутствовать
        new_id = json_data.get("id")
        self.assertIsNotNone(new_id)
        old = AdminKey.objects.get(pk=ak.pk)
        self.assertFalse(old.is_active)
        new = AdminKey.objects.get(pk=new_id)
        self.assertTrue(new.is_active)
        mock_send.assert_called()

    @patch("Users.tasks.send_admin_key_email.delay")
    def test_pending_requests_and_approve_request(self, mock_send):
        # создаём пользователя, который запросил ключ и не имеет AdminKey
        u = User.objects.create_user(email="req@a.aa", password="pw", role="admin")
        u.is_admin_key_required = True
        u.save()

        resp = self.client.get("/api/adminkeys/pending_requests/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        emails = {r.get("email") for r in data}
        self.assertIn(u.email, emails)

        # одобряем запрос
        resp2 = self.client.post(
            "/api/adminkeys/approve_request/", {"email": u.email}, format="json"
        )
        self.assertEqual(resp2.status_code, 200)
        # теперь для пользователя создан AdminKey
        self.assertTrue(AdminKey.objects.filter(user=u).exists())
        mock_send.assert_called()

    def test_non_admin_cannot_access(self):
        # обычный пользователь не из админов
        client2 = APIClient()
        regular = User.objects.create_user(
            email="reg2@a.aa", password="pw", is_staff=False, is_superuser=False
        )
        client2.force_authenticate(user=regular)
        resp = client2.get("/api/adminkeys/")
        self.assertEqual(resp.status_code, 403)
