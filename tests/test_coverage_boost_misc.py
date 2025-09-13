import importlib
import subprocess


def test_import_config_modules():
    # простая проверка импорта для выполнения кода на уровне модуля
    mod_asgi = importlib.import_module("config.asgi")
    assert hasattr(mod_asgi, "application")
    mod_wsgi = importlib.import_module("config.wsgi")
    assert hasattr(mod_wsgi, "application")
    mod_celery = importlib.import_module("config.celery")
    # celery приложение может быть названо 'app'
    assert hasattr(mod_celery, "app")


def test_start_celery_show_status_monkeypatch(monkeypatch):
    # Импортируем здесь, чтобы не запускать процесс при импорте модуля
    import start_celery

    class DummyCompleted:
        stdout = "OK"
        stderr = ""

    def fake_run(cmd, capture_output=True, text=True):
        return DummyCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)
    start_celery.show_status()
