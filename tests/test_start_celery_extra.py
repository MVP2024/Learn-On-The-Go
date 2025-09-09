from unittest.mock import patch

from django.test import TestCase

import start_celery


class StartCeleryRunTaskTests(TestCase):
    """Проверяем, что run_task запускает execute_from_command_line с корректными аргументами.

    Мы патчим input и django.core.management.execute_from_command_line чтобы не запускать реальную shell.
    """

    @staticmethod
    def test_run_task_invokes_execute_from_command_line():
        called = {}

        def fake_input(prompt=""):
            # Выбираем первую задачу
            return "1"

        def fake_exec(argv):
            # Простая проверка: ensure it's called with 'manage.py', 'shell', '-c', ...
            called["argv"] = list(argv)

        with patch("builtins.input", fake_input), patch(
            "django.core.management.execute_from_command_line", fake_exec
        ):
            # Запускаем run_task - внутри оно должно вызвать execute_from_command_line
            start_celery.run_task()

        assert "argv" in called
        assert isinstance(called["argv"], list)
        assert (
            called["argv"][0].endswith("manage.py") or called["argv"][0] == "manage.py"
        )
        # '-c' должен присутствовать в аргументах вызова
        assert any("-c" in str(a) for a in called["argv"])
