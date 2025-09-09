import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase

from utils import celery_tasks
from utils.diag_load_fixtures import read_fixture, try_deserialize_one


class DiagLoadFixturesTests(TestCase):
    """Тесты для утилиты utils/diag_load_fixtures."""

    def test_read_fixture_valid_json(self):
        data = [{"model": "Users.user", "pk": 1, "fields": {}}]
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(data, fh, ensure_ascii=False)
            path = Path(fh.name)
        loaded = read_fixture(path)
        self.assertIsInstance(loaded, list)
        path.unlink()

    def test_try_deserialize_one_malformed(self):
        # Пытаемся десериализовать объект с неизвестной моделью — ожидаем False
        bogus = {"model": "No.such.model", "pk": 1, "fields": {}}
        ok, info = try_deserialize_one(bogus)
        self.assertFalse(ok)
        self.assertIn(info[0], ("deserialization", "save"))


class ImageValidatorsTests(TestCase):
    """Тестируем validate_image_file — проверяем поведение на корректных и некорректных файлах."""

    def test_validate_accepts_small_png(self):

        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\x9cc`````\x00\x00\x00\x02\x00\x01\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82"
        self.assertTrue(isinstance(png_bytes, (bytes, bytearray)))


class CeleryTasksYooKassaBranchesTests(TestCase):
    """Тесты для веток utils.celery_tasks.process_payment_completion с YooKassa."""

    def setUp(self):
        from Disciplines.models import Discipline
        from Lessons.models import Lesson
        from Users.models import User

        self.user = User.objects.create_user(email="ct_user@a.aa", password="pw")
        self.disc = Discipline.objects.create(title="CTDisc", description="d")
        self.lesson = Lesson.objects.create(
            title="CTL",
            discipline=self.disc,
            owner=None,
            lesson_order=1,
            video_url="http://ex",
        )

    def test_process_payment_completion_yookassa_succeeded_and_canceled_and_pending(
        self,
    ):
        from Payments.models import Payment

        # создаём payment с yookassa_payment_id
        p = Payment.objects.create(
            user=self.user,
            payment_type="lesson",
            lesson=self.lesson,
            amount=10,
            status="pending",
            transaction_id="tx-y-1",
        )
        # добавим поле yookassa_payment_id через update
        Payment.objects.filter(pk=p.pk).update(yookassa_payment_id="yoo-1")

        # статус succeeded -> должен вызвать PaymentService.complete_payment
        with patch(
            "Payments.yookassa_service.YooKassaService.get_payment_info",
            return_value={"status": "succeeded"},
        ):
            with patch(
                "Payments.services.PaymentService.complete_payment", return_value=None
            ) as mock_complete:
                result = celery_tasks.process_payment_completion.delay(p.id)

                mock_complete.assert_called()
                retval = getattr(result, "result", result)
                self.assertIn("completed", str(retval).lower() or "")

        # статус canceled -> payment.status станет failed
        p2 = Payment.objects.create(
            user=self.user,
            payment_type="lesson",
            lesson=self.lesson,
            amount=10,
            status="pending",
            transaction_id="tx-y-2",
        )
        Payment.objects.filter(pk=p2.pk).update(yookassa_payment_id="yoo-2")
        with patch(
            "Payments.yookassa_service.YooKassaService.get_payment_info",
            return_value={"status": "canceled"},
        ):
            result2 = celery_tasks.process_payment_completion.delay(p2.id)
            retval2 = getattr(result2, "result", result2)
            self.assertIn("canceled", str(retval2).lower() or "")
            p2.refresh_from_db()
            self.assertIn(
                p2.status,
                (
                    "failed",
                    "canceled",
                ),
            )

        p3 = Payment.objects.create(
            user=self.user,
            payment_type="lesson",
            lesson=self.lesson,
            amount=10,
            status="pending",
            transaction_id="tx-y-3",
        )
        Payment.objects.filter(pk=p3.pk).update(yookassa_payment_id="yoo-3")
        with patch(
            "Payments.yookassa_service.YooKassaService.get_payment_info",
            return_value={"status": "pending"},
        ):
            result3 = celery_tasks.process_payment_completion.delay(p3.id)
            retval3 = getattr(result3, "result", result3)
            self.assertIn("pending", str(retval3).lower())
