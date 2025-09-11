import io
from unittest.mock import patch, MagicMock

from django.test import TestCase

import start_celery


class StartCeleryMoreTests(TestCase):
    """Дополнительные тесты для start_celery.py — покрываем варианты выбора в меню."""

    @patch("time.sleep", lambda *_: None)
    def test_choice_1_starts_worker_and_beat_and_handles_keyboardinterrupt(self):
        """Выбор 1: должен попытаться запустить worker и beat и корректно обработать KeyboardInterrupt.

        Подменяем subprocess.Popen: первый экземпляр — worker, второй — beat.
        Имитируем, что worker.wait() поднимает KeyboardInterrupt, чтобы ветка except
        выполнила terminate() на обоих процессах.
        """
        worker_mock = MagicMock()
        beat_mock = MagicMock()
        # Когда wait вызывается на worker -> KeyboardInterrupt
        worker_mock.wait.side_effect = KeyboardInterrupt()
        beat_mock.wait.return_value = None
        # Popen side_effect возвращает сначала worker, затем beat
        with patch("subprocess.Popen", side_effect=[worker_mock, beat_mock]) as popen_patch, patch(
            "builtins.input", return_value="1"
        ):
            # не должен прерывать тест
            start_celery.start_celery()

        # Убедимся, что Popen вызван дважды и terminate у обоих был вызван
        self.assertEqual(popen_patch.call_count, 2)
        worker_mock.terminate.assert_called()
        beat_mock.terminate.assert_called()

    def test_choice_2_runs_worker_via_subprocess_run(self):
        """Выбор 2: запустит worker через subprocess.run (без реального запуска)."""
        mock_run = MagicMock(return_value=MagicMock())
        with patch("subprocess.run", mock_run), patch("builtins.input", return_value="2"):
            start_celery.start_celery()

        # Должен быть вызов subprocess.run (внутри run must be called at least once)
        self.assertTrue(mock_run.called)
        called_args = mock_run.call_args[0][0]
        # Команда должна начинаться с исполняемого python (sys.executable)
        self.assertIsInstance(called_args, list)
        self.assertIn("celery", called_args)

    def test_choice_3_runs_beat_via_subprocess_run(self):
        """Выбор 3: запустит только beat через subprocess.run."""
        mock_run = MagicMock(return_value=MagicMock())
        with patch("subprocess.run", mock_run), patch("builtins.input", return_value="3"):
            start_celery.start_celery()

        self.assertTrue(mock_run.called)
        called_args = mock_run.call_args[0][0]
        self.assertIsInstance(called_args, list)
        self.assertIn("celery", called_args)

    def test_invalid_choice_prints_message(self):
        """Неверный выбор — печатает сообщение и выходит из функции без исключений."""
        with patch("builtins.input", return_value="invalid"), patch("sys.stdout", new=io.StringIO()) as fake_out:
            start_celery.start_celery()
            out = fake_out.getvalue()
            self.assertIn("Неверный выбор", out)
