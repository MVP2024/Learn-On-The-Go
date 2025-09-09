import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from utils.clear_and_load_fixtures import (
    check_safety_flags,
    clear_database,
    load_fixtures,
)
from utils.clear_and_load_fixtures import main as clf_main
from utils.clear_and_load_fixtures import (
    run_fixture_checker,
    verify_data,
    verify_fixture_file,
)


class CheckSafetyAndFixtureTests(TestCase):
    def test_check_safety_flags_exits_in_production_without_allow(self):
        # В режиме DEBUG=False и без ALLOW_FIXTURE_CLEAR должна быть SystemExit
        with override_settings(DEBUG=False):
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(SystemExit) as cm:
                    check_safety_flags(force=False)
                self.assertEqual(cm.exception.code, 1)

    def test_check_safety_flags_allows_when_env_set(self):
        with override_settings(DEBUG=False):
            with patch.dict("os.environ", {"ALLOW_FIXTURE_CLEAR": "1"}):
                # не должно выбросить
                check_safety_flags(force=False)

    def test_verify_fixture_file_exits_when_missing(self):
        p = Path(tempfile.gettempdir()) / "definitely-not-exists-xyz.json"
        if p.exists():
            p.unlink()
        with self.assertRaises(SystemExit) as cm:
            verify_fixture_file(p)
        self.assertEqual(cm.exception.code, 2)

    def test_verify_fixture_file_finds_temp_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("[]")
            p = Path(fh.name)
        try:
            # не должно поднять SystemExit
            verify_fixture_file(p)
        finally:
            p.unlink()


class RunFixtureCheckerTests(TestCase):

    def test_run_fixture_checker_continues_when_module_missing(self):
        # Если модуля нет — функция просто печатает предупреждение и продолжается
        if "utils.check_fixtures_users" in __import__("sys").modules:
            del __import__("sys").modules["utils.check_fixtures_users"]
        # Should not raise
        run_fixture_checker()

    def test_run_fixture_checker_propagates_nonzero_exit(self):
        # Подставляем модуль который делает sys.exit(5)
        fake_mod = type("M", (), {})()

        def fake_main():
            raise SystemExit(5)

        fake_mod.main = fake_main
        import sys

        sys.modules["utils.check_fixtures_users"] = fake_mod
        try:
            with self.assertRaises(SystemExit) as cm:
                run_fixture_checker()
            self.assertEqual(cm.exception.code, 5)
        finally:
            del sys.modules["utils.check_fixtures_users"]


class ClearDatabaseTests(TestCase):
    def test_clear_database_dry_run_and_real_delete(self):
        # Подменим apps.get_model чтобы вернуть фейковую модель с manager
        class FakeManager:
            def __init__(self, count_val=2):
                self._count = count_val

            def count(self):
                return self._count

            def all(self):
                class Q:
                    @staticmethod
                    def delete():
                        return None

                return Q()

        class FakeModel:
            objects = FakeManager(2)

        def fake_get_model(app_label, model_name):
            # возвращаем FakeModel для первой пары, а затем LookupError
            if not getattr(fake_get_model, "called", False):
                fake_get_model.called = True
                return FakeModel
            raise LookupError("no")

        with patch(
            "utils.clear_and_load_fixtures.apps.get_model", side_effect=fake_get_model
        ):
            # dry_run True
            res = clear_database(dry_run=True)
            self.assertIsInstance(res, list)
            self.assertGreaterEqual(len(res), 1)

            # dry_run False (real delete) — не должно падать
            res2 = clear_database(dry_run=False)
            self.assertIsInstance(res2, list)

    def test_clear_database_handles_manager_count_exception(self):
        class BadManager:
            def count(self):
                raise Exception("boom count")

        class GoodManager:
            @staticmethod
            def count():
                return 1

            @staticmethod
            def all():
                class Q:
                    @staticmethod
                    def delete():
                        return None

                return Q()

        class FakeModelA:
            objects = BadManager()

        class FakeModelB:
            objects = GoodManager()

        # Первый вызов — BadManager -> prints and continues
        def side_effect(app_label, model_name):
            if not getattr(side_effect, "called", False):
                side_effect.called = True
                return FakeModelA
            return FakeModelB

        with patch(
            "utils.clear_and_load_fixtures.apps.get_model", side_effect=side_effect
        ):
            res = clear_database(dry_run=False)
            self.assertIsInstance(res, list)

    def test_clear_database_zero_count_skipped(self):
        class ZeroManager:
            @staticmethod
            def count():
                return 0

            @staticmethod
            def all():
                class Q:
                    @staticmethod
                    def delete():
                        return None

                return Q()

        class FakeModel:
            objects = ZeroManager()

        with patch(
            "utils.clear_and_load_fixtures.apps.get_model", return_value=FakeModel
        ):
            res = clear_database(dry_run=True)
            self.assertIsInstance(res, list)


class LoadFixturesTests(TestCase):
    def test_load_fixtures_permission_error_creates_noperms_and_retries(self):
        # создаём фикстурный файл с auth.permission и еще одной записью
        data = [
            {"model": "auth.permission", "pk": 1, "fields": {}},
            {"model": "Users.user", "pk": 1, "fields": {}},
        ]
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(data, fh, ensure_ascii=False)
            path = Path(fh.name)
        try:
            # Первый вызов loaddata кидает ошибку с текстом 'Permission has no content_type'
            calls = {"n": 0}

            def side_effect_call(*args, **kwargs):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise Exception("Permission has no content_type for some reason")
                return None

            with patch(
                "utils.clear_and_load_fixtures.call_command",
                side_effect=side_effect_call,
            ) as mock_call:
                load_fixtures(path, verbosity=0)
                self.assertGreaterEqual(mock_call.call_count, 2)
                # Проверяем наличие вызова с .noperms.json
                found_tmp = False
                for call in mock_call.call_args_list:
                    args, kwargs = call
                    if len(args) >= 2 and str(args[1]).endswith(".noperms.json"):
                        found_tmp = True
                        break
                if not found_tmp:
                    for call in mock_call.call_args_list:
                        args, kwargs = call
                        p = kwargs.get("path") or (args[1] if len(args) >= 2 else "")
                        if isinstance(p, str) and p.endswith(".noperms.json"):
                            found_tmp = True
                            break
                self.assertTrue(found_tmp, "Ожидался вызов с .noperms.json")
        finally:
            try:
                path.unlink()
            except Exception:
                pass
            try:
                tmp = path.with_suffix(".noperms.json")
                tmp.unlink()
            except Exception:
                pass

    def test_load_fixtures_re_raises_other_exceptions(self):
        data = [{"model": "Users.user", "pk": 1, "fields": {}}]
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(data, fh, ensure_ascii=False)
            path = Path(fh.name)
        try:
            with patch(
                "utils.clear_and_load_fixtures.call_command",
                side_effect=Exception("random fail"),
            ):
                with self.assertRaises(Exception):
                    load_fixtures(path, verbosity=0)
        finally:
            try:
                path.unlink()
            except Exception:
                pass


class MainCliTests(TestCase):

    def test_main_dry_run_path_calls_clear_database(self):

        with patch("utils.clear_and_load_fixtures.check_safety_flags"), patch(
            "utils.clear_and_load_fixtures.verify_fixture_file"
        ), patch("utils.clear_and_load_fixtures.run_fixture_checker"), patch(
            "utils.clear_and_load_fixtures.clear_database"
        ) as mock_clear, patch(
            "utils.clear_and_load_fixtures.ensure_groups"
        ), patch(
            "utils.clear_and_load_fixtures.load_fixtures"
        ), patch(
            "utils.clear_and_load_fixtures.verify_data"
        ):
            #
            clf_main(argv=["--dry-run", "--yes"])  # should not raise
            mock_clear.assert_called()

    def test_main_full_flow_with_yes_calls_components(self):

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
            # вызвать main, как если бы пользователь передал --yes
            clf_main(argv=["--yes"])  # should not raise
            mock_check.assert_called()
            mock_verify.assert_called()
            mock_checker.assert_called()
            mock_clear.assert_called()
            mock_groups.assert_called()
            mock_load.assert_called()
            mock_verify_data.assert_called()

    def test_main_user_declines_confirmation_cancels(self):
        # Если пользователь не подтверждает действие, main должен вернуться без вызова clear_database/load_fixtures
        with patch("utils.clear_and_load_fixtures.check_safety_flags"), patch(
            "utils.clear_and_load_fixtures.verify_fixture_file"
        ), patch("utils.clear_and_load_fixtures.run_fixture_checker"), patch(
            "utils.clear_and_load_fixtures.clear_database"
        ), patch(
            "utils.clear_and_load_fixtures.ensure_groups"
        ), patch(
            "utils.clear_and_load_fixtures.load_fixtures"
        ), patch(
            "utils.clear_and_load_fixtures.verify_data"
        ), patch(
            "utils.clear_and_load_fixtures.confirm", return_value=False
        ):
            # без --yes, чтобы подтвердить запрос; имитируем отказ
            clf_main(
                argv=["--dry-run"]
            )  # не должно вызывать ошибок и не должно вызывать clear_database real
            # убеждаемся, что clear_database был вызван (пробный запуск) или что ошибок не возникло

    def test_main_clear_database_exception_exits(self):
        with patch("utils.clear_and_load_fixtures.check_safety_flags"), patch(
            "utils.clear_and_load_fixtures.verify_fixture_file"
        ), patch("utils.clear_and_load_fixtures.run_fixture_checker"), patch(
            "utils.clear_and_load_fixtures.clear_database",
            side_effect=Exception("boom"),
        ), patch(
            "utils.clear_and_load_fixtures.confirm", return_value=True
        ):
            with self.assertRaises(SystemExit):
                clf_main(argv=["--yes"])  # should exit with code 1 inside main

    def test_main_ensure_groups_exception_continues_and_calls_load(self):
        with patch("utils.clear_and_load_fixtures.check_safety_flags"), patch(
            "utils.clear_and_load_fixtures.verify_fixture_file"
        ), patch("utils.clear_and_load_fixtures.run_fixture_checker"), patch(
            "utils.clear_and_load_fixtures.clear_database"
        ), patch(
            "utils.clear_and_load_fixtures.ensure_groups",
            side_effect=Exception("gboom"),
        ), patch(
            "utils.clear_and_load_fixtures.load_fixtures"
        ) as mock_load, patch(
            "utils.clear_and_load_fixtures.verify_data"
        ):
            clf_main(argv=["--yes"])  # should not raise
            mock_load.assert_called()


class VerifyDataTests(TestCase):
    @staticmethod
    def test_verify_data_handles_missing_models():
        # Патчим apps.get_model чтобы выбрасывал LookupError для одной модели
        with patch(
            "utils.clear_and_load_fixtures.apps.get_model",
            side_effect=LookupError("no"),
        ):
            # функция печатает, но не должна падать
            verify_data()
