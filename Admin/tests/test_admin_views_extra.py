from unittest.mock import patch

from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from Admin.models import AdminKey
from Users.models import User


class AdminKeyViewExtraTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client = APIClient()
        # create superuser admin
        self.admin = User.objects.create_user(
            email="api_admin2@a.aa", password="pw", is_superuser=True, is_staff=True
        )
        self.client.force_authenticate(user=self.admin)

    def test_get_queryset_handles_django_http_request_with_get_params(self):
        # создаём активный и неактивный ключи
        user = User.objects.create_user(email="u1@a.aa", password="pw")
        AdminKey.objects.create(
            user=user, key="a-active", email=user.email, is_active=True
        )
        AdminKey.objects.create(
            user=None, key="b-inactive", email="x@y.z", is_active=False
        )

        # Django WSGIRequest (без DRF Request) — view.get_queryset должен корректно обработать request.GET
        from Admin.views import AdminKeyViewSet

        view = AdminKeyViewSet()
        django_req = self.factory.get("/dummy/?is_active=true")
        # не оборачиваем в rest_framework.request.Request — имитируем окружение, где нет query_params
        view.request = django_req
        qs = view.get_queryset()
        ids = set(qs.values_list("key", flat=True))
        self.assertIn("a-active", ids)
        self.assertNotIn("b-inactive", ids)

    @patch("Users.tasks.send_admin_key_email.delay")
    def test_resend_with_email_calls_send_task(self, mock_send):
        ak = AdminKey.objects.create(
            user=None, key="ak-resend", email="resend@a.aa", is_active=True
        )
        resp = self.client.post(f"/api/adminkeys/{ak.id}/resend/")
        self.assertEqual(resp.status_code, 200)
        mock_send.assert_called_once()

    @patch("Users.tasks.send_admin_key_email.delay")
    def test_regenerate_for_email_only_creates_new(self, mock_send):
        # admin key without user but with email -> regenerate should create new active key and deactivate old
        ak = AdminKey.objects.create(
            user=None, key="ak-old-email", email="solo@a.aa", is_active=True
        )
        resp = self.client.post(f"/api/adminkeys/{ak.id}/regenerate/")
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        new_id = data.get("id")
        self.assertIsNotNone(new_id)
        old = AdminKey.objects.get(pk=ak.pk)
        self.assertFalse(old.is_active)
        new = AdminKey.objects.get(pk=new_id)
        self.assertTrue(new.is_active)
        self.assertEqual(new.email, "solo@a.aa")
        mock_send.assert_called_once()

    def test_approve_request_missing_email_returns_400(self):
        resp = self.client.post("/api/adminkeys/approve_request/", {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_approve_request_user_not_found_returns_404(self):
        resp = self.client.post(
            "/api/adminkeys/approve_request/", {"email": "noone@x.y"}, format="json"
        )
        self.assertEqual(resp.status_code, 404)
