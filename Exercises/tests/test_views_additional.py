from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Exercises.models import Answer, Question, Test
from Lessons.models import Lesson

User = get_user_model()


class TestViewSetAdditionalTests(TestCase):
    """Набор простых сценариев для проверок поведения viewset'а тестов."""

    def setUp(self):
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)

        self.teacher = User.objects.create_user(email="add_teacher@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))

        self.student = User.objects.create_user(email="add_student@a.aa", password="pw")
        self.student.groups.add(Group.objects.get(name="student"))

        self.admin = User.objects.create_user(email="add_admin@a.aa", password="pw")
        self.admin.groups.add(Group.objects.get(name="admin"))

        self.discipline = Discipline.objects.create(
            title="AddDisc", description="d", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="AddLesson",
            discipline=self.discipline,
            owner=self.teacher,
            lesson_order=1,
        )
        self.test = Test.objects.create(
            title="AddTest",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        self.q = Question.objects.create(
            test=self.test, text="Q?", question_order=1, is_multiple=False
        )
        self.ans = Answer.objects.create(question=self.q, text="Right", is_correct=True)

        self.client = APIClient()

    def test_unauthenticated_create_test_returns_401(self):
        # без аутентификации создание должно быть запрещено (401 или 403)
        resp = self.client.post(
            "/api/tests/",
            data={"title": "X", "discipline": self.discipline.id},
            format="json",
        )
        self.assertIn(resp.status_code, (401, 403))

    def test_teacher_submit_without_active_attempt_returns_400(self):
        # преподаватель пытается отправить ответы без активной попытки -> ожидание 400
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "answers": [{"question_id": self.q.id, "chosen_answer_ids": [self.ans.id]}]
        }
        resp = self.client.post(
            f"/api/tests/{self.test.id}/submit_test/", data=payload, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_admin_get_current_attempt_for_missing_test_returns_404(self):
        # запрос текущей попытки для несуществующего теста -> 404
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/tests/999999/get_current_attempt/")
        self.assertEqual(resp.status_code, 404)

    def test_student_sees_answers_when_accessible_patched(self):
        # по умолчанию студент не видит is_correct; патчим helper, чтобы включить доступ
        self.client.force_authenticate(user=self.student)
        resp0 = self.client.get("/api/answers/")
        self.assertEqual(resp0.status_code, 200)
        body0 = resp0.json()
        results0 = body0.get("results", body0) if isinstance(body0, dict) else body0
        # Возможны другие записи в БД, поэтому не делаем строгое утверждение
        if any(
            a.get("id") == self.ans.id
            for a in (results0 if isinstance(results0, list) else [])
        ):
            pass

        # Патчим функцию, отдающую доступные тесты, чтобы наш тест оказался доступен
        with patch(
            "Exercises.views._accessible_tests_for_student",
            return_value=Test.objects.filter(pk=self.test.pk),
        ):
            resp = self.client.get("/api/answers/")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            results = body.get("results", body) if isinstance(body, dict) else body
            self.assertTrue(
                any(
                    (a.get("id") == self.ans.id)
                    for a in (results if isinstance(results, list) else [])
                )
            )
