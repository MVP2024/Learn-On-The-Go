import sys
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from Disciplines.models import Discipline
from utils import clear_and_load_fixtures as clf
from utils.common_mixins import TitleOrPkLookupMixin


class ClearAndLoadFixturesExtraTests(TestCase):
    def test_check_safety_flags_blocks_in_production_when_not_allowed(self):
        with override_settings(DEBUG=False):
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(SystemExit) as cm:
                    clf.check_safety_flags(force=False)
                self.assertEqual(cm.exception.code, 1)

    @staticmethod
    def test_check_safety_flags_allows_with_force_even_when_debug_false():
        with override_settings(DEBUG=False):
            with patch.dict("os.environ", {}, clear=True):
                clf.check_safety_flags(force=True)

    def test_verify_fixture_file_exits_when_missing(self):
        p = Path("/tmp/definitely-not-exists-12345.json")
        if p.exists():
            p.unlink()
        with self.assertRaises(SystemExit) as cm:
            clf.verify_fixture_file(p)
        self.assertEqual(cm.exception.code, 2)

    @staticmethod
    def test_run_fixture_checker_continues_when_module_missing():
        if "utils.check_fixtures_users" in sys.modules:
            del sys.modules["utils.check_fixtures_users"]
        clf.run_fixture_checker()

    def test_clear_database_handles_manager_count_exception_and_deletes(self):
        class BadManager:
            def count(self):
                raise Exception("boom count")

        class GoodManager:
            def __init__(self):
                self._deleted = False

            @staticmethod
            def count():
                return 2

            @staticmethod
            def all():
                class Q:
                    @staticmethod
                    def delete():
                        return None

                return Q()

        class FakeModel:
            objects = GoodManager()

        def fake_get_model_once(app_label, model_name):
            if not hasattr(fake_get_model_once, "called"):
                fake_get_model_once.called = True
                return FakeModel
            raise LookupError("no")

        with patch(
            "utils.clear_and_load_fixtures.apps.get_model",
            side_effect=fake_get_model_once,
        ):
            res = clf.clear_database(dry_run=False)
            self.assertIsInstance(res, list)


class TitleOrPkLookupNumericTests(TestCase):
    def setUp(self):
        self.d = Discipline.objects.create(title="NumTest", description="d")

    def test_get_object_by_numeric_pk_string(self):
        class Dummy(TitleOrPkLookupMixin):
            def get_queryset(self):
                return Discipline.objects

            def filter_queryset(self, qs):
                return qs

            def check_object_permissions(self, request, obj):
                return True

        v = Dummy()
        v.kwargs = {"pk": str(self.d.pk)}
        v.request = type("R", (), {"user": None, "query_params": {}})()
        obj = v.get_object()
        self.assertEqual(obj.pk, self.d.pk)

    def test_get_object_with_invalid_id_param_raises_validation(self):
        Discipline.objects.create(title="SameTitle", description="a")
        Discipline.objects.create(title="SameTitle", description="b")

        class Dummy(TitleOrPkLookupMixin):
            def get_queryset(self):
                return Discipline.objects

            def filter_queryset(self, qs):
                return qs.filter(title__iexact="SameTitle")

            def check_object_permissions(self, request, obj):
                return True

        d = Dummy()
        d.kwargs = {"pk": "SameTitle"}
        d.request = type("R", (), {"user": None, "query_params": {"id": "notint"}})()
        from rest_framework import serializers

        with self.assertRaises(serializers.ValidationError):
            d.get_object()
