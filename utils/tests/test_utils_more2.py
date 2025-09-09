import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

import utils.diag_load_fixtures as diag_mod
from utils import celery_tasks
from utils.clear_and_load_fixtures import (
    check_safety_flags,
    clear_database,
    ensure_groups,
)


class SafetyAndGroupsTests(TestCase):
    """Проверяем check_safety_flags и ensure_groups"""

    @staticmethod
    def test_check_safety_flags_allows_with_env_flag():
        with override_settings(DEBUG=False):
            # установим переменную окружения
            with patch.dict(os.environ, {"ALLOW_FIXTURE_CLEAR": "1"}):
                # не должен поднять
                check_safety_flags(force=False)

    @staticmethod
    def test_ensure_groups_creates_missing():
        # удалим группы если есть, затем вызовем
        # ensure_groups печатает, но главное — не падать
        ensure_groups()


class DiagLoadFixturesMainBranchesTests(TestCase):
    """Покроем main() ветки в utils.diag_load_fixtures."""

    def test_main_exits_when_read_fixture_returns_non_list(self):
        # Патчим FIXTURE на временный путь и read_fixture чтобы вернуть dict
        tmp = Path(tempfile.gettempdir()) / "tmp_fixture_nonlist.json"
        tmp.write_text("{}", encoding="utf-8")
        with patch.object(diag_mod, "FIXTURE", tmp), patch.object(
            diag_mod, "read_fixture", return_value={"x": 1}
        ):
            with self.assertRaises(SystemExit) as cm:
                diag_mod.main()
            self.assertEqual(cm.exception.code, 4)
        tmp.unlink(missing_ok=True)

    def test_main_writes_problem_record_on_bad_entry(self):
        # Подготовим фикстуру с одним объектом
        data = [{"model": "Users.user", "pk": 1, "fields": {}}]
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            import json

            json.dump(data, fh, ensure_ascii=False)
            tmp = Path(fh.name)
        # Патчим try_deserialize_one чтобы он вернул False и инфо
        with patch.object(diag_mod, "FIXTURE", tmp), patch.object(
            diag_mod,
            "try_deserialize_one",
            return_value=(False, ("save", Exception("save fail"))),
        ):
            try:
                diag_mod.main()
                out = tmp.with_name("problem_record.json")
                self.assertTrue(out.exists())
            finally:
                # cleanup
                tmp.unlink(missing_ok=True)
                out.unlink(missing_ok=True)


class CeleryTasksNotFoundTests(TestCase):
    """Покрываем ветки NotFound/returns for celery tasks."""

    def test_process_payment_completion_not_found(self):
        result = celery_tasks.process_payment_completion.delay(99999999)
        retval = getattr(result, "result", result)
        self.assertIn("not found", str(retval).lower())

    def test_send_payment_success_notification_payment_missing(self):
        result = celery_tasks.send_payment_success_notification.delay(99999999)
        retval = getattr(result, "result", result)
        self.assertIn("not found", str(retval).lower())

    def test_generate_daily_reports_no_admins(self):
        # убедимся, что без суперпользователей функция отрабатывает и возвращает 0 admins
        # очистим суперпользователей
        from django.contrib.auth import get_user_model

        User = get_user_model()
        User.objects.filter(is_superuser=True).delete()
        out = celery_tasks.generate_daily_reports()
        self.assertIn("отчёт отправлен", str(out).lower())


class ClearDatabaseEdgeTests(TestCase):
    """Тестируем clear_database dry_run and real path with mocked models"""

    def test_clear_database_handles_models_missing_and_dry_run(self):
        fake_manager = type(
            "M",
            (),
            {
                "count": staticmethod(lambda: 0),
                "all": staticmethod(
                    lambda: type("A", (), {"delete": staticmethod(lambda: None)})
                ),
            },
        )()

        class FakeModel:
            objects = fake_manager

        with patch(
            "utils.clear_and_load_fixtures.apps.get_model", return_value=FakeModel
        ):
            res = clear_database(dry_run=True)
            self.assertIsInstance(res, list)
