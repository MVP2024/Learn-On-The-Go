from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Exercises.models import Answer, Question, QuizAttempt, Test
from Lessons.models import Lesson, UserLessonProgress

User = get_user_model()


class TestViewSetExtraTests(TestCase):
    """Различные сценарии поведения viewset'а тестов (доступы, старт/submit, retrieve)."""

    def setUp(self):
        # создаём стандартные группы
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)

        # пользователи
        self.teacher = User.objects.create_user(email="tv_extra@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))
        self.student = User.objects.create_user(email="st_extra@a.aa", password="pw")
        self.student.groups.add(Group.objects.get(name="student"))
        self.admin = User.objects.create_user(email="adm_extra2@a.aa", password="pw")
        self.admin.groups.add(Group.objects.get(name="admin"))

        # дисциплина/урок/тест
        self.discipline = Discipline.objects.create(
            title="Dextra", description="d", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="Lextra",
            discipline=self.discipline,
            owner=self.teacher,
            lesson_order=1,
        )
        self.test = Test.objects.create(
            title="Extra Test",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        self.q = Question.objects.create(
            test=self.test, text="Q?", question_order=1, is_multiple=False
        )
        self.a_ok = Answer.objects.create(question=self.q, text="OK", is_correct=True)
        self.a_bad = Answer.objects.create(
            question=self.q, text="Bad", is_correct=False
        )

        self.client = APIClient()

    def test_student_cannot_create_test_returns_403(self):
        # студент не может создавать тесты
        self.client.force_authenticate(user=self.student)
        resp = self.client.post(
            "/api/tests/",
            data={"title": "ShouldFail", "discipline": self.discipline.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_retrieve_by_duplicate_title_no_id_returns_404_and_with_bad_id_returns_400(
        self,
    ):
        # создаём два теста с одинаковым title и проверяем поведение retrieve
        Test.objects.create(
            title="DupTitle",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        Test.objects.create(
            title="DupTitle",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        self.client.force_authenticate(user=self.admin)

        # без ?id -> неоднозначность -> 404
        resp = self.client.get("/api/tests/DupTitle/")
        self.assertEqual(resp.status_code, 404)

        # с неправильным id -> 400
        resp2 = self.client.get("/api/tests/DupTitle/?id=abc")
        self.assertEqual(resp2.status_code, 400)

        # с числовым id, но не входящим в совпадения -> 404
        resp3 = self.client.get("/api/tests/DupTitle/?id=999999")
        self.assertEqual(resp3.status_code, 404)

    def test_submit_test_student_without_access_and_no_attempt_returns_403(self):
        # студент без завершённого урока не имеет доступа
        self.client.force_authenticate(user=self.student)
        payload = {
            "answers": [{"question_id": self.q.id, "chosen_answer_ids": [self.a_ok.id]}]
        }
        resp = self.client.post(
            f"/api/tests/{self.test.id}/submit_test/", data=payload, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_submit_test_with_active_attempt_and_invalid_answer_returns_400(self):
        # даём доступ и создаём активную попытку, затем отправляем несуществующий id ответа
        UserLessonProgress.objects.create(
            user=self.student, lesson=self.lesson, is_completed=True
        )
        QuizAttempt.objects.create(
            user=self.student, quiz=self.test, is_completed=False
        )
        self.client.force_authenticate(user=self.student)
        payload = {
            "answers": [{"question_id": self.q.id, "chosen_answer_ids": [999999]}]
        }
        resp = self.client.post(
            f"/api/tests/{self.test.id}/submit_test/", data=payload, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_start_test_marks_previous_attempt_completed_and_creates_new(self):
        # студент имеет доступ к уроку; старая попытка должна пометиться завершённой, создаётся новая
        UserLessonProgress.objects.create(
            user=self.student, lesson=self.lesson, is_completed=True
        )
        old = QuizAttempt.objects.create(
            user=self.student, quiz=self.test, is_completed=False
        )
        self.client.force_authenticate(user=self.student)
        resp = self.client.post(f"/api/tests/{self.test.id}/start_test/")
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        new_id = data.get("id")
        self.assertIsNotNone(new_id)
        old.refresh_from_db()
        self.assertTrue(old.is_completed)
        new_attempt = QuizAttempt.objects.get(id=new_id)
        self.assertFalse(new_attempt.is_completed)

    def test_get_current_attempt_returns_active_attempt_even_if_no_access(self):
        # студент не имеет формального доступа, но у него есть активная попытка
        active = QuizAttempt.objects.create(
            user=self.student, quiz=self.test, is_completed=False
        )
        self.client.force_authenticate(user=self.student)
        resp = self.client.get(f"/api/tests/{self.test.id}/get_current_attempt/")
        # ожидаем 200 потому что активная попытка допускается независимо от доступа
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("id"), active.id)

    def test_retrieve_by_pk_returns_404_for_missing(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/tests/999999/")
        self.assertEqual(resp.status_code, 404)

    def test_retrieve_by_pk_returns_test(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(f"/api/tests/{self.test.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("id"), self.test.id)
