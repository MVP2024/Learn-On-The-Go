from unittest.mock import Mock

from django.test import TestCase

from utils.celery_tasks import TaskWrapper


class TaskWrapperExtraTests(TestCase):
    """Тесты для TaskWrapper: поведение retry и fallback веток."""

    def test_celery_retry_returns_value_is_forwarded(self):
        """Если celery_task.retry возвращает значение — оно возвращается wrapper.run."""

        def impl_raises():
            raise ValueError("impl boom")

        mock_celery = Mock()
        mock_celery.retry.return_value = "retried-result"

        wrapper = TaskWrapper(impl_raises, celery_task=mock_celery)

        res = wrapper.run(wrapper, 1, kw=2)
        self.assertEqual(res, "retried-result")
        mock_celery.retry.assert_called()

    def test_wrapper_retry_fallback_used_when_no_celery_task(self):
        """Если celery_task отсутствует — используется fallback self.retry."""

        def impl_raises():
            raise RuntimeError("boom")

        wrapper = TaskWrapper(impl_raises, celery_task=None)

        # Патчим retry на инстанс, чтобы вернуть специальное значение
        setattr(wrapper, "retry", lambda exc=None: "fallback-handled")

        res = wrapper.run(wrapper, 1)
        self.assertEqual(res, "fallback-handled")

    def test_direct_call_invokes_impl(self):
        """Прямой вызов wrapper(...) вызывает внутреннюю реализацию _impl и возвращает результат."""

        def impl_ok(x, y=0):
            return "ok", x, y

        w = TaskWrapper(impl_ok, celery_task=None)
        self.assertEqual(w(5, y=7), ("ok", 5, 7))
