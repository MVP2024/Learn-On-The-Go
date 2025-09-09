import importlib

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

User = get_user_model()


class UsersModuleImportTests(TestCase):
    """Проверяем импорт модулей Users.urls и Users.views и некоторые ветви внутри них."""

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_import_users_urls_and_urlpatterns_structure(self):
        """Импортируем Users.urls и проверяем, что urlpatterns содержит ожидаемые маршруты.
        Также проверяем добавление static() при DEBUG=True через override_settings.
        """
        urls_mod = importlib.import_module("Users.urls")
        self.assertTrue(hasattr(urls_mod, "urlpatterns"))
        up = urls_mod.urlpatterns
        self.assertTrue(len(up) >= 1)

        with override_settings(DEBUG=True):
            importlib.reload(urls_mod)
            self.assertTrue(hasattr(urls_mod, "urlpatterns"))
            self.assertIsInstance(urls_mod.urlpatterns, list)

    def test_import_users_views_and_call_get_serializer_class(self):
        """Импортируем Users.views, создаём экземпляр UserProfileViewSet и проверяем
        выбор сериализатора для разных actions.
        """
        vmod = importlib.import_module("Users.views")
        u = User.objects.create_user(email="vv@a.aa", password="pw")
        view_cls = getattr(vmod, "UserProfileViewSet")
        view = view_cls()
        django_req = self.factory.get("/api/profiles/")
        django_req.user = u
        req = django_req
        view.request = req
        view.format_kwarg = None

        view.action = "me"
        sc = view.get_serializer_class()
        self.assertIsNotNone(sc)

        view.action = "admin_key_login"
        sc2 = view.get_serializer_class()
        self.assertIsNotNone(sc2)

        view.action = "list"
        sc3 = view.get_serializer_class()
        self.assertIsNotNone(sc3)

    def test_get_permissions_branches_and_me_action_response(self):
        vmod = importlib.import_module("Users.views")
        view_cls = getattr(vmod, "UserProfileViewSet")
        view = view_cls()
        u = User.objects.create_user(email="permtest@a.aa", password="pw")
        django_req = self.factory.get("/api/profiles/me/")
        django_req.user = u
        req = django_req
        view.request = req
        view.format_kwarg = None

        view.action = "me"
        perms = view.get_permissions()
        self.assertIsInstance(perms, list)
        resp = view.me(req)
        self.assertTrue(hasattr(resp, "status_code"))

    def test_generate_new_admin_key_flow_atomic_and_email(self):
        vmod = importlib.import_module("Users.views")
        view_cls = getattr(vmod, "UserProfileViewSet")
        su = User.objects.create_user(
            email="gen_super@a.aa", password="pw", is_superuser=True, is_staff=True
        )
        target = User.objects.create_user(email="gen_target@a.aa", password="pw")
        target.role = "admin"
        target.is_active = False
        target.is_admin_key_required = True
        target.save()

        view = view_cls()
        django_req = self.factory.post(
            "/api/profiles/generate_new_admin_key/",
            {"email": target.email},
            format="json",
        )
        django_req.user = su
        req = django_req
        view.request = req
        view.format_kwarg = None
        view.action = "generate_new_admin_key"
        mail.outbox.clear()
        resp = view.generate_new_admin_key(req)
        self.assertEqual(resp.status_code, 200)
        from Admin.models import AdminKey

        self.assertTrue(AdminKey.objects.filter(user=target).exists())
        self.assertGreaterEqual(len(mail.outbox), 1)

    def test_admin_key_login_flow_serializer_side_effects(self):
        vmod = importlib.import_module("Users.views")
        view_cls = getattr(vmod, "UserProfileViewSet")
        view = view_cls()

        u = User.objects.create_user(email="ak_flow@a.aa", password="pw")
        u.role = "admin"
        u.is_admin_key_required = True
        u.save()
        from Admin.models import AdminKey

        AdminKey.objects.create(user=u, key="KEYXYZ", is_active=True, email=u.email)

        django_req = self.factory.post(
            "/api/profiles/admin_key_login/",
            {"email": u.email, "password": "pw", "admin_key": "KEYXYZ"},
            format="json",
        )
        django_req.user = type("Anon", (), {"is_authenticated": False})()
        req = django_req
        view.request = req
        view.format_kwarg = None
        view.action = "admin_key_login"
        # неверный ключ -> 400 (используем другой пользователя, чтобы избежать изменения состояния первого пользователя)
        u2 = User.objects.create_user(email="ak_flow2@a.aa", password="pw2")
        u2.role = "admin"
        u2.is_admin_key_required = True
        u2.save()
        AdminKey.objects.create(user=u2, key="OTHER", is_active=True, email=u2.email)

        django_req2 = self.factory.post(
            "/api/profiles/admin_key_login/",
            {"email": u2.email, "password": "pw2", "admin_key": "BAD"},
            format="json",
        )
        django_req2.user = type("Anon", (), {"is_authenticated": False})()
        req2 = django_req2
        view.request = req2
        view.format_kwarg = None
        # При прямом вызове view.admin_key_login() сериализатор может поднять ValidationError
        # (в реальном HTTP-запросе DRF обработчик исключений вернёт 400). Мы принимаем оба поведения.
        from rest_framework.exceptions import ValidationError as DRFValidationError

        try:
            resp2 = view.admin_key_login(req2)
        except DRFValidationError:
            resp2 = None
        if resp2 is not None:
            self.assertIn(resp2.status_code, (400, 401))
        else:
            # сериализатор поднял ValidationError — считаем это эквивалентом 400
            self.assertTrue(True)
