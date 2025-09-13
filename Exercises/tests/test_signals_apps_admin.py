import importlib
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase

from Disciplines.models import Discipline
from Exercises.apps import ExercisesConfig
from Exercises.models import Test as QuizTest

User = get_user_model()


class SignalsAppsAdminTests(TestCase):
    """Тесты для сигналов, apps и admin регистрации."""

    def setUp(self):
        self.user = User.objects.create_user(email="a@a.com", password="pw")
        self.disc = Discipline.objects.create(
            title="S", description="d", owner=self.user
        )

    def test_cache_cleared_on_save_and_delete(self):
        t = QuizTest.objects.create(title="C", discipline=self.disc, owner=self.user)
        with patch("django.core.cache.cache.delete") as mock_delete:
            t.title = "C2"
            t.save()
            mock_delete.assert_called_with(f"/exercises/{t.pk}/")
        with patch("django.core.cache.cache.delete") as mock_delete2:
            pk = t.pk
            t.delete()
            mock_delete2.assert_called_with(f"/exercises/{pk}/")

    @staticmethod
    def test_app_ready_imports_signals_safely():
        # Создаём AppConfig корректно: передаём app_name и app_module
        exercises_module = importlib.import_module("Exercises")
        cfg = ExercisesConfig("Exercises", exercises_module)  # Исправлено имя класса
        cfg.ready()  # не должно выбросить исключение

    def test_admin_registered_models(self):
        # Убедимся, что основные модели зарегистрированы в админке
        from Exercises import models as tests_models

        for model in [tests_models.Test, tests_models.Question, tests_models.Answer]:
            self.assertIn(model, admin.site._registry)
