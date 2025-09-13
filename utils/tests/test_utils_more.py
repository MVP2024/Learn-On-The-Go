import sys
import types
from unittest.mock import patch

from django.test import TestCase, override_settings

from Disciplines.models import Discipline
from Lessons.models import Lesson
from Payments.models import Payment
from Users.models import User
from utils import celery_tasks
from utils.clear_and_load_fixtures import (
    check_safety_flags,
    load_fixtures,
    run_fixture_checker,
    verify_fixture_file,
)


class CeleryTasksRetryBranchTests(TestCase):
    """Покрываем ветку except -> self.retry в process_payment_completion."""

    def setUp(self):
        self.user = User.objects.create_user(email="ct_rb@a.aa", password="pw")
        self.disc = Discipline.objects.create(title="CTRB", description="d")
        self.lesson = Lesson.objects.create(
            title="Lcr",
            discipline=self.disc,
            owner=None,
            lesson_order=1,
            video_url="http://ex",
        )

    def test_process_payment_completion_calls_retry_on_unhandled_exception(self):
        # создаём pending payment
        p = Payment.objects.create(
            user=self.user,
            payment_type="lesson",
            lesson=self.lesson,
            amount=10,
            status="pending",
            transaction_id="tx-rb-1",
        )
        # сделаем так, чтобы PaymentService.complete_payment поднял исключение
        with patch(
            "Payments.services.PaymentService.complete_payment",
            side_effect=Exception("boom"),
        ):
            # патчим retry на самом celery task объекте, чтобы он бросал RuntimeError и мы могли поймать вызов
            celery_task = getattr(
                celery_tasks.process_payment_completion, "_celery_task", None
            )
            if celery_task is not None:
                with patch.object(
                    celery_task, "retry", side_effect=RuntimeError("task retried")
                ):
                    # вызываем run напрямую — это вызовет retry синхронно и пробросит RuntimeError
                    with self.assertRaises(RuntimeError):
                        celery_tasks.process_payment_completion.run(
                            celery_tasks.process_payment_completion, p.id
                        )
            else:
                # если celery_task отсутствует — патчим wrapper.retry
                with patch.object(
                    celery_tasks.process_payment_completion,
                    "retry",
                    side_effect=RuntimeError("task retried"),
                ):
                    with self.assertRaises(RuntimeError):
                        celery_tasks.process_payment_completion.run(
                            celery_tasks.process_payment_completion, p.id
                        )

        # Мокаем serializers.deserialize, возвращаем iterator с объектом, у которого есть save()
        class FakeObj:
            @staticmethod
            def save():
                # ничего не делаем — save проходит
                return None

        with patch(
            "utils.diag_load_fixtures.serializers.deserialize",
            return_value=iter([FakeObj()]),
        ):
            from utils.diag_load_fixtures import try_deserialize_one

            ok, info = try_deserialize_one(
                {"model": "Users.user", "pk": 1, "fields": {}}
            )
            self.assertTrue(ok)
            self.assertIsNone(info)


class ClearAndLoadFixturesMainAndHelpersTests(TestCase):
    """Тестируем разные ветки utils.clear_and_load_fixtures: dry-run main, load_fixtures success, run_fixture_checker failure handling."""

    @staticmethod
    def test_check_safety_flags_allows_in_debug():
        with override_settings(DEBUG=True):
            # не должен поднять SystemExit
            check_safety_flags(force=False)

    @staticmethod
    def test_verify_fixture_file_finds_temp_file():
        with open("temp_fixture_empty.json", "w", encoding="utf-8") as fh:
            fh.write("[]")
        try:
            verify_fixture_file(__import__("pathlib").Path("temp_fixture_empty.json"))
        finally:
            import os

            os.unlink("temp_fixture_empty.json")

    @staticmethod
    def test_load_fixtures_success_calls_loaddata():
        # создаём временный json и патчим call_command
        data = [{"model": "Users.user", "pk": 1, "fields": {}}]
        import json
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(data, fh, ensure_ascii=False)
            path = __import__("pathlib").Path(fh.name)
        try:
            with patch("utils.clear_and_load_fixtures.call_command") as mock_call:
                load_fixtures(path, verbosity=0)
                mock_call.assert_called()
        finally:
            try:
                path.unlink()
            except Exception:
                pass

    def test_run_fixture_checker_handles_systemexit_nonzero(self):
        # Подставляем модуль utils.check_fixtures_users который при вызове main делает sys.exit(5)
        fake_mod = types.ModuleType("utils.check_fixtures_users")

        def fake_main():
            raise SystemExit(5)

        fake_mod.main = fake_main
        sys.modules["utils.check_fixtures_users"] = fake_mod
        try:
            with self.assertRaises(SystemExit) as cm:
                run_fixture_checker()
            self.assertEqual(cm.exception.code, 5)
        finally:
            del sys.modules["utils.check_fixtures_users"]
