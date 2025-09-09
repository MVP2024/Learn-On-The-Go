from django.test import RequestFactory, TestCase
from rest_framework.response import Response

from utils.cache_mixins import RetrieveCacheMixin
from utils.common_mixins import OwnerCreateMixin


class DummyBase:
    @staticmethod
    def retrieve(request, *args, **kwargs):
        return Response({"ok": True})


class ViewWithBase(RetrieveCacheMixin, DummyBase):
    pass


class CacheMixinsTests(TestCase):
    """Тесты для utils.cache_mixins и небольших методов в common_mixins."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_retrieve_returns_404_when_no_base(self):
        # Класс, у которого нет базового retrieve
        class NoBase(RetrieveCacheMixin):
            pass

        inst = NoBase()
        req = self.factory.get("/test/")
        # В случае отсутствия базового retrieve ожидаем Response с 404
        resp = inst.retrieve(req)
        self.assertEqual(resp.status_code, 404)

    def test_retrieve_calls_super_when_present(self):
        inst = ViewWithBase()
        req = self.factory.get("/test/")
        resp = inst.retrieve(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {"ok": True})

    def test_get_related_instance_helper_none_and_instance(self):
        # Тестируем OwnerCreateMixin._get_related_instance
        class DummyModel:
            def __init__(self, pk):
                self.pk = pk

        # Подставляем модель и объект
        inst = OwnerCreateMixin()
        # Передаём экземпляр — должен вернуть его же
        obj = DummyModel(1)
        got = inst._get_related_instance(obj, DummyModel)
        self.assertIs(got, obj)
        # Если передать None — вернётся None
        self.assertIsNone(inst._get_related_instance(None, DummyModel))
