from unittest.mock import patch

from django.test import TestCase

from Disciplines.models import Discipline
from utils import diag_load_fixtures
from utils.clear_and_load_fixtures import main as clf_main
from utils.common_mixins import TitleOrPkLookupMixin


class TitleOrPkLookupSlugTests(TestCase):
    """Покрываем ветку slug в TitleOrPkLookupMixin.get_object"""

    def setUp(self):
        self.d = Discipline.objects.create(title="SlugDis", description="d")

    def test_get_object_by_slug_when_field_exists(self):
        # создаём фиктивный viewset, который использует TitleOrPkLookupMixin
        class Dummy(TitleOrPkLookupMixin):
            def get_queryset(self):
                return Discipline.objects

            def filter_queryset(self, qs):
                return qs

            def check_object_permissions(self, request, obj):
                return True

        # убедимся, что model has slug
        v = Dummy()
        v.kwargs = {"pk": self.d.slug}
        v.request = type("R", (), {"user": None, "query_params": {}})()
        obj = v.get_object()
        self.assertIsNotNone(obj)
        self.assertEqual(obj.slug, self.d.slug)


class ClearAndLoadFixturesFullFlowTests(TestCase):
    """Тестируем полный путь main() в clear_and_load_fixtures с моками."""

    @staticmethod
    def test_clf_main_full_flow_calls_components():
        with patch(
            "utils.clear_and_load_fixtures.check_safety_flags"
        ) as mock_check, patch(
            "utils.clear_and_load_fixtures.verify_fixture_file"
        ) as mock_verify, patch(
            "utils.clear_and_load_fixtures.run_fixture_checker"
        ) as mock_checker, patch(
            "utils.clear_and_load_fixtures.clear_database"
        ) as mock_clear, patch(
            "utils.clear_and_load_fixtures.ensure_groups"
        ) as mock_groups, patch(
            "utils.clear_and_load_fixtures.load_fixtures"
        ) as mock_load, patch(
            "utils.clear_and_load_fixtures.verify_data"
        ) as mock_verify_data:
            # вызываем main с параметром --yes, чтобы пропустить запрос
            clf_main(argv=["--yes"])  # should not raise
            mock_check.assert_called()
            mock_verify.assert_called()
            mock_checker.assert_called()
            mock_clear.assert_called()
            mock_groups.assert_called()
            mock_load.assert_called()
            mock_verify_data.assert_called()


class DiagLoadFixturesMainSuccessTests(TestCase):
    """Покрываем успешный проход main() в diag_load_fixtures — все десериализуются успешно."""

    @staticmethod
    def test_diag_main_success_path():
        # Подменим read_fixture чтобы вернуть список объектов, и try_deserialize_one вернуть True
        fake_data = [{"model": "Users.user", "pk": 1, "fields": {}}]
        with patch.object(
            diag_load_fixtures, "read_fixture", return_value=fake_data
        ), patch.object(
            diag_load_fixtures, "try_deserialize_one", return_value=(True, None)
        ):
            # main должен отработать и вернуть None (печатает результат)
            diag_load_fixtures.main()
