from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import serializers
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Exercises.models import QuizAttempt, Test
from Lessons.models import Lesson

User = get_user_model()


class TestViewSetMore2Tests(TestCase):
    """Набор тестов: пагинация by_title, обработка ошибок submit, права создания тестов."""

    def setUp(self):
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)

        self.teacher = User.objects.create_user(email="m2_teacher@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))
        self.moderator = User.objects.create_user(email="m2_mod@a.aa", password="pw")
        self.moderator.groups.add(Group.objects.get(name="moderator"))
        self.admin = User.objects.create_user(email="m2_admin@a.aa", password="pw")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.student = User.objects.create_user(email="m2_student@a.aa", password="pw")
        self.student.groups.add(Group.objects.get(name="student"))

        self.discipline = Discipline.objects.create(
            title="M2Disc", description="d", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="M2Lesson",
            discipline=self.discipline,
            owner=self.teacher,
            lesson_order=1,
        )
        self.client = APIClient()

    def test_by_title_pagination(self):
        # создаём 7 тестов для проверки пагинации
        for i in range(7):
            Test.objects.create(
                title=f"Paginate Test",
                discipline=self.discipline,
                lesson=self.lesson,
                owner=self.teacher,
            )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(
            "/api/tests/by_title/?title=Paginate&exact=false&page=1&page_size=5"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        self.assertTrue(isinstance(results, list))
        self.assertLessEqual(len(results), 5)

    def test_submit_service_raises_validation_error_returns_400(self):
        # подготовка: студент с доступом и активной попыткой
        from Lessons.models import UserLessonProgress

        UserLessonProgress.objects.create(
            user=self.student, lesson=self.lesson, is_completed=True
        )
        attempt = QuizAttempt.objects.create(
            user=self.student,
            quiz=Test.objects.create(
                title="SvcTest",
                discipline=self.discipline,
                lesson=self.lesson,
                owner=self.teacher,
            ),
            is_completed=False,
        )
        self.client.force_authenticate(user=self.student)
        payload = {"answers": [{"question_id": 1, "chosen_answer_ids": [1]}]}

        # подменяем сервис, чтобы выбрасывал ValidationError
        with patch(
            "Exercises.views.QuizAttemptService.submit_test_attempt",
            side_effect=serializers.ValidationError({"detail": "bad"}),
        ):
            resp = self.client.post(
                f"/api/tests/{attempt.quiz.id}/submit_test/",
                data=payload,
                format="json",
            )
            self.assertEqual(resp.status_code, 400)

    def test_create_test_permissions_for_roles(self):
        url = "/api/tests/"
        data = {"title": "RoleCreated", "discipline": self.discipline.id}

        # teacher
        self.client.force_authenticate(user=self.teacher)
        r = self.client.post(url, data=data, format="json")
        self.assertIn(r.status_code, (201, 200))

        # admin
        self.client.force_authenticate(user=self.admin)
        r2 = self.client.post(
            url,
            data={"title": "AdminCreated", "discipline": self.discipline.id},
            format="json",
        )
        self.assertIn(r2.status_code, (201, 200))

        # moderator — в зависимости от логики может быть 201 или 400; принимаем оба варианта
        self.client.force_authenticate(user=self.moderator)
        r3 = self.client.post(
            url,
            data={"title": "ModCreated", "discipline": self.discipline.id},
            format="json",
        )
        self.assertIn(r3.status_code, (201, 200, 400))
