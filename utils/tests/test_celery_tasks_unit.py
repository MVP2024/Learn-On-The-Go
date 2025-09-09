from unittest.mock import Mock

from django.test import TestCase

import utils.celery_tasks as ct
from utils.celery_tasks import TaskWrapper


class CeleryTasksUnitTests(TestCase):
    """Простые unit-тесты для utils.celery_tasks.

    Тестируют экспорт имён задач, простое поведение обёртки TaskWrapper и
    корректную установку модульных имён, которые используются в тестах проекта.
    """

    def test_tasks_names_exported_and_module_level_aliases(self):
        """Проверяем, что имена задач присутствуют в __all__ и доступны как переменные модуля.

        Это покрывает участок, где модуль формирует __all__ и создаёт явные
        переменные cleanup_expired_admin_keys и т.д., чтобы статические импорты работали.
        """
        # ожидание: ключевые задачи объявлены в модуле и доступны по имени
        expected = [
            "cleanup_expired_payments",
            "cleanup_expired_discounts",
            "cleanup_expired_admin_keys",
            "generate_daily_reports",
            "update_user_progress_stats",
            "send_course_reminders",
            "process_payment_completion",
            "send_payment_success_notification",
            "generate_payment_analytics",
        ]
        for name in expected:
            self.assertIn(name, getattr(ct, "__all__", []), msg=f"{name} не в __all__")
            # и переменная в модуле доступна
            self.assertTrue(hasattr(ct, name), msg=f"модуль не имеет атрибута {name}")
            # значение должно быть TaskWrapper (или None if something failed to create)
            val = getattr(ct, name)
            self.assertTrue(
                (isinstance(val, TaskWrapper) or val is None),
                msg=f"{name} имеет неверный тип: {type(val)}",
            )

    def test_taskwrapper_run_tries_celery_retry_then_wrapper_retry(self):
        """Если реализация бросает исключение — TaskWrapper сначала вызывает celery_task.retry,
        если тот бросает, то падает дальше (мы проверяем цепочку вызовов).
        """

        # реализация, которая всегда бросает
        def impl_raises():
            raise ValueError("impl boom")

        # celery_task.retry будет бросать RuntimeError — это симулирует поведение теста
        mock_celery_task = Mock()
        mock_celery_task.retry.side_effect = RuntimeError("task retried")

        wrapper = TaskWrapper(impl_raises, celery_task=mock_celery_task)

        with self.assertRaises(RuntimeError):
            # вызываем run: первый аргумент — self (симулируем bound task)
            wrapper.run(wrapper, 1, kw=2)

        mock_celery_task.retry.assert_called()

    def test_taskwrapper_delay_and_apply_async_fallback(self):
        """Проверяем, что delay/apply_async используют celery-таску когда она есть,
        иначе выполняют синхронно реализацию.
        """

        def impl_ok(x, y=0):
            return "ok", x, y

        # без celery_task — вызывается impl
        w_no_celery = TaskWrapper(impl_ok, celery_task=None)
        res = w_no_celery.delay(5, y=7)
        self.assertEqual(res, ("ok", 5, 7))
        res2 = w_no_celery.apply_async(3, y=4)
        self.assertEqual(res2, ("ok", 3, 4))

        # с celery_task имеющим delay/apply_async — их результат возвращается
        mock_cel = Mock()
        mock_cel.delay.return_value = "delayed-result"
        mock_cel.apply_async.return_value = "applied-result"
        w_with_celery = TaskWrapper(impl_ok, celery_task=mock_cel)
        self.assertEqual(w_with_celery.delay(1), "delayed-result")
        self.assertEqual(w_with_celery.apply_async(2), "applied-result")

    def test_process_payment_completion_wrapper_points_to_impl(self):
        """Убедимся, что process_payment_completion представлен как TaskWrapper
        и внутри хранит реализацию _process_payment_completion_impl.
        """
        obj = getattr(ct, "process_payment_completion")
        # объект должен быть TaskWrapper
        self.assertTrue(isinstance(obj, TaskWrapper))
        # внутренняя реализация должна быть callable
        impl = getattr(obj, "_impl", None)
        self.assertTrue(callable(impl))
        # имя реализации должно содержать 'process_payment_completion' для диагностики
        self.assertIn("process_payment_completion", getattr(impl, "__name__", ""))
