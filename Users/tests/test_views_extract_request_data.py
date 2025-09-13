from django.test import TestCase

from Users.views import UserProfileViewSet


class ExtractRequestDataTests(TestCase):
    """Проверяем вспомогательный метод _extract_request_data для разных типов request."""

    def test_extract_from_drf_request(self):
        # Объект с атрибутом data (DRF Request)
        req = type("R", (), {"data": {"a": 1}})()
        res = UserProfileViewSet._extract_request_data(req)
        self.assertEqual(res, {"a": 1})

    def test_extract_from_wsgi_post(self):
        req = type("R", (), {"POST": {"b": "2"}})()
        res = UserProfileViewSet._extract_request_data(req)
        self.assertEqual(res, {"b": "2"})

    def test_extract_from_raw_body_json(self):
        body = b'{"c": 3}'
        req = type("R", (), {"body": body})()
        res = UserProfileViewSet._extract_request_data(req)
        self.assertEqual(res, {"c": 3})

    def test_extract_returns_empty_for_unparsable(self):
        req = type("R", (), {"body": b"not-json"})()
        res = UserProfileViewSet._extract_request_data(req)
        self.assertEqual(res, {})
