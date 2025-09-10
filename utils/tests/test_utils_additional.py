from unittest.mock import patch

from django.test import TestCase

import utils.celery_tasks as celery_tasks


class CeleryTasksYooKassaBranchesTests(TestCase):
    """Покрываем ветку utils.celery_tasks.process_payment_completion с YooKassa."""

    def setUp(self):
        from Disciplines.models import Discipline
        from Lessons.models import Lesson
        from Users.models import User

        self.user = User.objects.create_user(email="ct_rb@a.aa", password="pw")
        self.disc = Discipline.objects.create(title="CTRB", description="d")
        self.lesson = Lesson.objects.create(
            title="Lcr",
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
                # Prefer machine-friendly status field; fallback to text checks for compatibility
                if isinstance(retval, dict):
                    self.assertEqual(retval.get("status"), "completed")
                else:
                    text = str(retval).lower() if retval is not None else ""
                    self.assertTrue(
                        ("completed" in text) or ("заверш" in text),
                        msg=f"Ожидался маркер завершения в ответе, получили: {text}",
                    )

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
            if isinstance(retval2, dict):
                self.assertIn(retval2.get("status"), ("failed", "canceled"))
            else:
                text2 = str(retval2).lower() if retval2 is not None else ""
                # accept english or russian words indicating canceled/failed
                self.assertTrue(
                    any(k in text2 for k in ("canceled", "cancellation", "failed", "отмен", "неудач")),
                    msg=f"Ожидался маркер отмены/failed в ответе, получили: {text2}",
                )
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
            if isinstance(retval3, dict):
                self.assertEqual(retval3.get("status"), "pending")
            else:
                text3 = str(retval3).lower() if retval3 is not None else ""
                self.assertTrue(any(k in text3 for k in ("pending", "в процессе", "ожида")), msg=f"Ожидался маркер pending в ответе, получили: {text3}")

