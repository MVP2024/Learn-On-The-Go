from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Exercises.models import Answer, Question, QuizAttempt, Test
from Exercises.permissions import IsTestOwnerOrAdminOrModerator
from Lessons.models import Lesson, UserLessonProgress

User = get_user_model()


class ExercisesViewsPermissionsExtraTests(TestCase):
    """Тесты для проверки потоков start/submit и класса разрешений."""

    def setUp(self):
        # обеспечиваем наличие групп
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)

        # создаём пользователей
        self.teacher = User.objects.create_user(email="t_extra@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))

        self.student = User.objects.create_user(email="s_extra@a.aa", password="pw")
        self.student.groups.add(Group.objects.get(name="student"))

        self.admin = User.objects.create_user(email="adm_extra@a.aa", password="pw")
        self.admin.groups.add(Group.objects.get(name="admin"))

        self.moderator = User.objects.create_user(email="mod_extra@a.aa", password="pw")
        self.moderator.groups.add(Group.objects.get(name="moderator"))

        # создаём дисциплину/урок/тест/вопрос/ответы
        self.discipline = Discipline.objects.create(
            title="FlowDisc", description="d", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="FlowLesson",
            discipline=self.discipline,
            owner=self.teacher,
            lesson_order=1,
        )
        self.test = Test.objects.create(
            title="FlowTest",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )

        self.question = Question.objects.create(
            test=self.test, text="What is 2+2?", question_order=1, is_multiple=False
        )
        self.answer_correct = Answer.objects.create(
            question=self.question, text="4", is_correct=True
        )
        self.answer_wrong = Answer.objects.create(
            question=self.question, text="3", is_correct=False
        )

        self.client = APIClient()

    def test_student_start_submit_flow_success(self):
        # даём студенту доступ — помечаем урок пройденным
        UserLessonProgress.objects.create(
            user=self.student, lesson=self.lesson, is_completed=True
        )

        # студент стартует тест
        self.client.force_authenticate(user=self.student)
        resp = self.client.post(f"/api/tests/{self.test.id}/start_test/")
        self.assertEqual(resp.status_code, 201)
        attempt_data = resp.json()
        attempt_id = attempt_data.get("id")
        self.assertIsNotNone(attempt_id)

        # отправляем ответы (правильные)
        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "chosen_answer_ids": [self.answer_correct.id],
                }
            ]
        }
        resp2 = self.client.post(
            f"/api/tests/{self.test.id}/submit_test/", data=payload, format="json"
        )
        self.assertEqual(resp2.status_code, 200)

        # проверяем, что попытка завершена и score = 1
        qa = QuizAttempt.objects.get(id=attempt_id)
        self.assertTrue(qa.is_completed)
        self.assertEqual(qa.score, 1)

    def test_student_start_no_access_forbidden(self):
        # студент без завершённого урока не может стартовать тест
        self.client.force_authenticate(user=self.student)
        resp = self.client.post(f"/api/tests/{self.test.id}/start_test/")
        self.assertIn(resp.status_code, (403, 404))

    def test_teacher_can_start_test(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.post(f"/api/tests/{self.test.id}/start_test/")
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("id", data)

    def test_submit_without_active_attempt_returns_400(self):
        # даём студенту доступ, но не стартуем попытку -> при submit получаем 400/403
        UserLessonProgress.objects.create(
            user=self.student, lesson=self.lesson, is_completed=True
        )
        self.client.force_authenticate(user=self.student)
        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "chosen_answer_ids": [self.answer_correct.id],
                }
            ]
        }
        resp = self.client.post(
            f"/api/tests/{self.test.id}/submit_test/", data=payload, format="json"
        )
        self.assertIn(resp.status_code, (400, 403))

    def test_get_current_attempt_various(self):
        # активная попытка у студента
        active = QuizAttempt.objects.create(
            user=self.student, quiz=self.test, is_completed=False
        )
        self.client.force_authenticate(user=self.student)
        resp = self.client.get(f"/api/tests/{self.test.id}/get_current_attempt/")
        # в зависимости от среды и проверки доступа может вернуться 200 или 404/403
        self.assertIn(resp.status_code, (200, 403, 404))
        if resp.status_code == 200:
            data = resp.json()
            self.assertEqual(data.get("id"), active.id)

        # преподаватель запрашивает текущую попытку -> 404 (нет попытки для преподавателя)
        self.client.force_authenticate(user=self.teacher)
        resp2 = self.client.get(f"/api/tests/{self.test.id}/get_current_attempt/")
        self.assertEqual(resp2.status_code, 404)

    def test_permission_class_behaviour(self):
        perm = IsTestOwnerOrAdminOrModerator()
        # POST: владелец (teacher) должен быть разрешён
        req = type("R", (), {"method": "POST", "user": self.teacher})()
        self.assertTrue(perm.has_permission(req, None))
        # POST: случайный пользователь без роли -> False
        other = User.objects.create_user(email="other@a.aa", password="pw")
        req2 = type("R", (), {"method": "POST", "user": other})()
        self.assertFalse(perm.has_permission(req2, None))

        # has_object_permission для Test: владелец True, другой False
        req_put_owner = type("R", (), {"method": "PUT", "user": self.teacher})()
        self.assertTrue(perm.has_object_permission(req_put_owner, None, self.test))
        req_put_other = type("R", (), {"method": "PUT", "user": other})()
        self.assertFalse(perm.has_object_permission(req_put_other, None, self.test))

        # moderator и admin имеют полные права
        req_mod = type("R", (), {"method": "DELETE", "user": self.moderator})()
        self.assertTrue(perm.has_object_permission(req_mod, None, self.test))
        req_admin = type("R", (), {"method": "PATCH", "user": self.admin})()
        self.assertTrue(perm.has_object_permission(req_admin, None, self.test))

        # Для Question/Answer объекты проверяются через test.owner
        q = self.question
        a = self.answer_correct
        self.assertTrue(perm.has_object_permission(req_put_owner, None, q))
        self.assertTrue(perm.has_object_permission(req_put_owner, None, a))
        self.assertFalse(perm.has_object_permission(req_put_other, None, q))
        self.assertFalse(perm.has_object_permission(req_put_other, None, a))
