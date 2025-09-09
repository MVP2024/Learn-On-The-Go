from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient, APITestCase

from Disciplines.models import Discipline
from Exercises.models import Answer, Question, QuizAttempt, Test
from Lessons.models import Lesson, UserLessonProgress

User = get_user_model()


def resp_body(response):
    """
    Безопасно извлекает тело ответа как Python-объект.
    Сначала пробует response.json(), затем response.data или пустой словарь.
    """
    if hasattr(response, "json"):
        try:
            return response.json()
        except Exception:
            pass
    return getattr(response, "data", {})


class StudentTestAccessFlowTests(APITestCase):
    """Покрывает сценарий доступа студента к тестам и прохождения теста.

    Сценарий:
    1) Студент без завершённого урока не видит тест.
    2) Попытка начать тест до завершения урока — 403/404.
    3) После отметки урока завершённым тест виден, студент может начать и сдать тест.
    4) После сдачи студент видит поле is_correct для ответов.
    """

    def setUp(self):
        # создаём группы
        for g in ["teacher", "student", "admin", "moderator"]:
            Group.objects.get_or_create(name=g)

        # создаём учителя и студента
        self.teacher = User.objects.create_user(
            email="teacher_flow@a.aa", password="testpass"
        )
        Group.objects.get(name="teacher")
        self.teacher.groups.add(Group.objects.get(name="teacher"))

        self.student = User.objects.create_user(
            email="student_flow@a.aa", password="testpass"
        )
        self.student.groups.add(Group.objects.get(name="student"))

        # дисциплина, урок и тест
        self.discipline = Discipline.objects.create(
            title="Flow Discipline", description="Desc", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="Flow Lesson",
            discipline=self.discipline,
            owner=self.teacher,
            lesson_order=1,
            video_url="http://example.com/video",
        )

        self.test = Test.objects.create(
            title="Lesson Test",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )

        # вопрос и ответы
        self.question = Question.objects.create(
            test=self.test, text="What is 1+1?", question_order=1, is_multiple=False
        )
        self.answer1 = Answer.objects.create(
            question=self.question, text="2", is_correct=True
        )
        self.answer2 = Answer.objects.create(
            question=self.question, text="3", is_correct=False
        )

        self.api_client: APIClient = APIClient()
        self.api_client.force_authenticate(user=self.student)

    def test_student_cannot_see_test_before_lesson_completion_and_can_after(self):
        # 1) без аутентификации — 401
        self.api_client.logout()
        resp = self.api_client.get("/api/tests/")
        self.assertEqual(resp.status_code, 401)

        # 2) аутентифицированный студент — тест не виден
        self.api_client.force_authenticate(user=self.student)
        resp = self.api_client.get("/api/tests/")
        self.assertEqual(resp.status_code, 200)
        tests_list = resp.json()
        body = (
            tests_list.get("results", tests_list)
            if isinstance(tests_list, dict)
            else tests_list
        )
        self.assertTrue(all(t.get("id") != self.test.id for t in body))

        # попытка начать тест должна быть запрещена
        resp = self.api_client.post(f"/api/tests/{self.test.id}/start_test/")
        self.assertIn(resp.status_code, (403, 404))

        # 3) отмечаем урок как завершённый
        UserLessonProgress.objects.create(
            user=self.student, lesson=self.lesson, is_completed=True
        )

        # теперь тест должен быть виден
        resp = self.api_client.get("/api/tests/")
        self.assertEqual(resp.status_code, 200)
        tests_list = resp.json()
        body = (
            tests_list.get("results", tests_list)
            if isinstance(tests_list, dict)
            else tests_list
        )
        self.assertTrue(any(t.get("id") == self.test.id for t in body))

        # 4) начинаем тест
        resp = self.api_client.post(f"/api/tests/{self.test.id}/start_test/")
        self.assertEqual(resp.status_code, 201)
        attempt = resp.json()
        self.assertIn("id", attempt)

        # отправляем ответ
        payload = {
            "answers": [
                {
                    "question_id": self.question.id,
                    "chosen_answer_ids": [self.answer1.id],
                }
            ]
        }
        resp = self.api_client.post(
            f"/api/tests/{self.test.id}/submit_test/", data=payload, format="json"
        )
        self.assertEqual(resp.status_code, 200)

        # проверяем, что попытка завершена и начислен балл
        qa = QuizAttempt.objects.get(user=self.student, quiz=self.test)
        self.assertTrue(qa.is_completed)
        self.assertEqual(qa.score, 1)

        # после сдачи студент видит details теста и поле is_correct
        resp = self.api_client.get(f"/api/tests/{self.test.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        questions = data.get("questions", [])
        self.assertTrue(len(questions) > 0)
        ans_list = questions[0].get("answers", [])
        found = False
        for a in ans_list:
            if a.get("id") == self.answer1.id:
                found = True
                self.assertIn("is_correct", a)
                self.assertTrue(a["is_correct"])
        self.assertTrue(found)


class TestViewSetFunctionalityTests(APITestCase):
    """Дополнительные функциональные проверки TestViewSet (списки, создание/обновление/удаление)."""

    def setUp(self):
        for g in ["teacher", "student", "admin", "moderator"]:
            Group.objects.get_or_create(name=g)
        self.teacher_user = User.objects.create_user(
            email="teacher@example.com", password="password"
        )
        self.teacher_user.groups.add(Group.objects.get(name="teacher"))

        self.student_user = User.objects.create_user(
            email="student@example.com", password="password"
        )
        self.student_user.groups.add(Group.objects.get(name="student"))

        self.admin_user = User.objects.create_user(
            email="admin@example.com", password="password", is_superuser=True
        )
        self.admin_user.groups.add(Group.objects.get(name="admin"))

        self.moderator_user = User.objects.create_user(
            email="moderator@example.com", password="password"
        )
        self.moderator_user.groups.add(Group.objects.get(name="moderator"))

        self.discipline1 = Discipline.objects.create(
            title="Math", description="Math", owner=self.teacher_user
        )
        self.discipline2 = Discipline.objects.create(
            title="Science", description="Science", owner=self.teacher_user
        )

        self.lesson1_disc1 = Lesson.objects.create(
            title="Lesson 1 Math",
            discipline=self.discipline1,
            owner=self.teacher_user,
            lesson_order=1,
            video_url="http://example.com/video1",
        )
        self.lesson2_disc1 = Lesson.objects.create(
            title="Lesson 2 Math",
            discipline=self.discipline1,
            owner=self.teacher_user,
            lesson_order=2,
            video_url="http://example.com/video2",
        )

        self.test1_lesson1 = Test.objects.create(
            title="Test 1 Lesson 1",
            discipline=self.discipline1,
            lesson=self.lesson1_disc1,
            owner=self.teacher_user,
        )
        self.test2_discipline1 = Test.objects.create(
            title="Test 2 Discipline 1",
            discipline=self.discipline1,
            lesson=None,
            owner=self.teacher_user,
        )

        self.question1_test1 = Question.objects.create(
            test=self.test1_lesson1,
            text="Q1 for Test 1",
            question_order=1,
            is_multiple=False,
        )
        self.answer1_q1 = Answer.objects.create(
            question=self.question1_test1, text="A1 Correct", is_correct=True
        )
        self.answer2_q1 = Answer.objects.create(
            question=self.question1_test1, text="A2 Wrong", is_correct=False
        )

        self.client = APIClient()

    def test_list_tests_admin_sees_all(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/tests/")
        self.assertEqual(response.status_code, 200)
        body = resp_body(response)
        # ожидаем корректное число
        self.assertEqual(body.get("count"), Test.objects.count())

    def test_list_tests_teacher_sees_own_and_unowned(self):
        other_teacher = User.objects.create_user(
            email="other_teacher@example.com", password="password"
        )
        other_teacher.groups.add(Group.objects.get(name="teacher"))
        Discipline.objects.create(
            title="Other Disc", description="Other", owner=other_teacher
        )
        Test.objects.create(
            title="Other Teacher Test", discipline=self.discipline2, owner=other_teacher
        )

        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.get("/api/tests/")
        self.assertEqual(response.status_code, 200)
        body = resp_body(response)
        results = body.get("results", []) if isinstance(body, dict) else body
        self.assertTrue(any(t.get("id") == self.test1_lesson1.id for t in results))
        self.assertEqual(
            body.get("count"), Test.objects.filter(owner=self.teacher_user).count()
        )

    def test_list_tests_student_sees_accessible(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get("/api/tests/")
        self.assertEqual(response.status_code, 200)
        body = resp_body(response)
        self.assertEqual(body.get("count"), 0)

        UserLessonProgress.objects.create(
            user=self.student_user, lesson=self.lesson1_disc1, is_completed=True
        )
        response = self.client.get("/api/tests/")
        self.assertEqual(response.status_code, 200)
        body = resp_body(response)
        self.assertEqual(body.get("count"), 1)

        UserLessonProgress.objects.create(
            user=self.student_user, lesson=self.lesson2_disc1, is_completed=True
        )
        response = self.client.get("/api/tests/")
        self.assertEqual(response.status_code, 200)
        body = resp_body(response)
        self.assertEqual(body.get("count"), 2)

    def test_retrieve_test(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f"/api/tests/{self.test1_lesson1.id}/")
        self.assertEqual(response.status_code, 200)
        body = resp_body(response)
        self.assertEqual(body.get("id"), self.test1_lesson1.id)
        self.assertIn("questions", body)

    def test_create_test_teacher_success(self):
        self.client.force_authenticate(user=self.teacher_user)
        data = {
            "title": "New Test by Teacher",
            "description": "Desc",
            "discipline": self.discipline1.id,
            "lesson": self.lesson1_disc1.id,
        }
        response = self.client.post("/api/tests/", data, format="json")
        self.assertEqual(response.status_code, 201)
        body = resp_body(response)
        self.assertEqual(body.get("owner"), self.teacher_user.id)

    def test_create_test_student_forbidden(self):
        self.client.force_authenticate(user=self.student_user)
        data = {
            "title": "New Test by Student",
            "description": "Desc",
            "discipline": self.discipline1.id,
        }
        response = self.client.post("/api/tests/", data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_update_test_owner_success(self):
        self.client.force_authenticate(user=self.teacher_user)
        data = {"title": "Updated Test Title"}
        response = self.client.patch(
            f"/api/tests/{self.test1_lesson1.id}/", data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        body = resp_body(response)
        self.assertEqual(body.get("title"), "Updated Test Title")

    def test_update_test_non_owner_forbidden(self):
        other_teacher = User.objects.create_user(
            email="non_owner@example.com", password="password"
        )
        other_teacher.groups.add(Group.objects.get(name="teacher"))
        self.client.force_authenticate(user=other_teacher)
        data = {"title": "Attempt to Update"}
        response = self.client.patch(
            f"/api/tests/{self.test1_lesson1.id}/", data, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_test_owner_success(self):
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.delete(f"/api/tests/{self.test1_lesson1.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Test.objects.filter(id=self.test1_lesson1.id).exists())

    def test_delete_test_moderator_success(self):
        self.client.force_authenticate(user=self.moderator_user)
        response = self.client.delete(f"/api/tests/{self.test1_lesson1.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Test.objects.filter(id=self.test1_lesson1.id).exists())

    def test_start_test_student_no_access(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.post(f"/api/tests/{self.test1_lesson1.id}/start_test/")
        self.assertEqual(response.status_code, 403)
        body = resp_body(response)
        self.assertIn("Доступ к этому тесту закрыт", str(body.get("detail", body)))

    def test_start_test_student_with_access(self):
        UserLessonProgress.objects.create(
            user=self.student_user, lesson=self.lesson1_disc1, is_completed=True
        )
        self.client.force_authenticate(user=self.student_user)
        response = self.client.post(f"/api/tests/{self.test1_lesson1.id}/start_test/")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            QuizAttempt.objects.filter(
                user=self.student_user, quiz=self.test1_lesson1, is_completed=False
            ).exists()
        )

    def test_start_test_teacher_success(self):
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.post(f"/api/tests/{self.test1_lesson1.id}/start_test/")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            QuizAttempt.objects.filter(
                user=self.teacher_user, quiz=self.test1_lesson1, is_completed=False
            ).exists()
        )

    def test_submit_test_invalid_attempt(self):
        UserLessonProgress.objects.create(
            user=self.student_user, lesson=self.lesson1_disc1, is_completed=True
        )
        self.client.force_authenticate(user=self.student_user)
        data = {
            "answers": [
                {
                    "question_id": self.question1_test1.id,
                    "chosen_answer_ids": [self.answer1_q1.id],
                }
            ]
        }
        response = self.client.post(
            f"/api/tests/{self.test1_lesson1.id}/submit_test/", data, format="json"
        )
        self.assertIn(response.status_code, (400, 403))
        if response.status_code == 400:
            body = (
                response.json()
                if hasattr(response, "json")
                else getattr(response, "data", {})
            )
            self.assertIn("Активная попытка прохождения теста не найдена", str(body))
        else:
            body = (
                response.json()
                if hasattr(response, "json")
                else getattr(response, "data", {})
            )
            self.assertIn("Доступ к этому тесту закрыт", str(body))

    def test_get_current_attempt_with_active_attempt(self):
        UserLessonProgress.objects.create(
            user=self.student_user, lesson=self.lesson1_disc1, is_completed=True
        )
        active_attempt = QuizAttempt.objects.create(
            user=self.student_user, quiz=self.test1_lesson1, is_completed=False
        )
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(
            f"/api/tests/{self.test1_lesson1.id}/get_current_attempt/"
        )
        self.assertEqual(response.status_code, 200)
        body = resp_body(response)
        self.assertEqual(body.get("id"), active_attempt.id)
        self.assertFalse(body.get("is_completed"))

    def test_get_current_attempt_teacher_access_ok(self):
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.get(
            f"/api/tests/{self.test1_lesson1.id}/get_current_attempt/"
        )
        self.assertEqual(response.status_code, 404)
