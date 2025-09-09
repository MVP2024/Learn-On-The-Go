from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from Admin.models import AdminKey
from Users.views import UserProfileViewSet

User = get_user_model()


class UserViewsAdditionalTests(TestCase):
    def setUp(self):
        self.super = User.objects.create_user(
            email="su2@a.aa", password="pw", is_superuser=True, is_staff=True
        )
        self.user = User.objects.create_user(email="u_view@a.aa", password="pw")

    def test_me_action_returns_user_profile(self):
        view = UserProfileViewSet()
        req = type("R", (), {"user": self.user})()
        view.request = req
        view.format_kwarg = None
        view.action = "me"
        resp = view.me(req)
        self.assertTrue(hasattr(resp, "status_code"))

    def test_generate_new_admin_key_forbidden_for_non_superuser(self):
        view = UserProfileViewSet()
        req = type("R", (), {"user": self.user, "body": b"", "data": {}})()
        view.request = req
        view.format_kwarg = None
        view.action = "generate_new_admin_key"
        resp = view.generate_new_admin_key(req)
        self.assertEqual(resp.status_code, 403)

    @patch("Users.views.send_admin_key_email.delay")
    def test_generate_new_admin_key_creates_adminkey_and_sends(self, mock_send):
        target = User.objects.create_user(email="target@a.aa", password="pw")
        view = UserProfileViewSet()
        body = {"email": target.email}
        req = type("R", (), {"user": self.super, "data": body})()
        view.request = req
        view.format_kwarg = None
        view.action = "generate_new_admin_key"
        resp = view.generate_new_admin_key(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(AdminKey.objects.filter(user=target).exists())
        mock_send.assert_called()

    def test_request_admin_key_user_not_found_returns_404(self):
        view = UserProfileViewSet()
        req = type("R", (), {"data": {"email": "noone@example.com"}})()
        view.request = req
        view.format_kwarg = None
        view.action = "request_admin_key"
        resp = view.request_admin_key(req)
        self.assertEqual(resp.status_code, 404)

    def test_request_admin_key_wrong_role_returns_400(self):
        u = User.objects.create_user(email="plain@a.aa", password="pw")
        view = UserProfileViewSet()
        req = type("R", (), {"data": {"email": u.email}})()
        view.request = req
        view.format_kwarg = None
        view.action = "request_admin_key"
        resp = view.request_admin_key(req)
        self.assertEqual(resp.status_code, 400)

    def test_extract_request_data_prefers_data_over_post_and_body(self):
        req = type("R", (), {"data": {"a": 1}, "POST": {"a": 2}, "body": b"{}"})()
        res = UserProfileViewSet._extract_request_data(req)
        self.assertEqual(res, {"a": 1})

    def test_extract_request_data_parses_json_body(self):
        req = type("R", (), {"body": b'{"k": "v"}'})()
        res = UserProfileViewSet._extract_request_data(req)
        self.assertEqual(res, {"k": "v"})
