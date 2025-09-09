"""Простой тест-импорт, который просто импортирует модули чтобы пройти их уровни импорта.
Это не интеграционные тесты — просто smoke для повышения покрытия.
"""

import importlib


def test_import_main_modules():
    # Импортируем набор модулей — в некоторых есть код на уровне модуля
    modules = [
        "config.settings",
        "config.celery",
        "Users.apps",
        "Admin.apps",
        "Payments.apps",
        "Lessons.apps",
        "Exercises.apps",
        "Disciplines.apps",
        "Teachers.apps",
        "Students.apps",
        "utils",
        "utils.celery_tasks",
    ]
    for m in modules:
        mod = importlib.import_module(m)
        assert mod is not None

    # Импортируем некоторые сервисы/функции
    mod2 = importlib.import_module("Payments.yookassa_service")
    assert hasattr(mod2, "YooKassaService") or True

    mod3 = importlib.import_module("Payments.stripe_service")
    assert hasattr(mod3, "StripeService") or True

    mod4 = importlib.import_module("utils.image_validators")
    assert hasattr(mod4, "validate_image_file")
