from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Exercises.models import Answer, Question, QuizAttempt, Test
from Lessons.models import Lesson, UserLessonProgress

User = get_user_model()


class TestViewSetCoverageTests(TestCase):
    """Покрываем распространённые сценарии работы TestViewSet."""

    def setUp(self):
        # создаём группы
        for g in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=g)

        # пользователи
        self.teacher = User.objects.create_user(email="t_cov@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))
        self.teacher2 = User.objects.create_user(email="t2_cov@a.aa", password="pw")
        self.teacher2.groups.add(Group.objects.get(name="teacher"))

        self.student = User.objects.create_user(email="s_cov@a.aa", password="pw")
        self.student.groups.add(Group.objects.get(name="student"))

        self.admin = User.objects.create_user(email="adm_cov@a.aa", password="pw")
        self.admin.groups.add(Group.objects.get(name="admin"))

        self.mod = User.objects.create_user(email="mod_cov@a.aa", password="pw")
        self.mod.groups.add(Group.objects.get(name="moderator"))

        # дисциплина + урок
        self.discipline = Discipline.objects.create(
            title="CovDisc", description="d", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="CovLesson",
            discipline=self.discipline,
            owner=self.teacher,
            lesson_order=1,
        )

        # тесты
        self.test_a = Test.objects.create(
            title="A Test",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        self.test_b = Test.objects.create(
            title="B Test",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        self.test_c = Test.objects.create(
            title="C Test", discipline=self.discipline, lesson=None, owner=self.teacher
        )

        # вопрос и ответы
        self.question = Question.objects.create(
            test=self.test_a, text="What is 1+1?", question_order=1, is_multiple=False
        )
        self.ans_ok = Answer.objects.create(
            question=self.question, text="2", is_correct=True
        )
        self.ans_bad = Answer.objects.create(
            question=self.question, text="3", is_correct=False
        )

        self.client = APIClient()

    def test_list_ordering_and_visibility(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/tests/")
        assert resp.status_code == 200
        data = resp.json()
        body = data.get("results", data) if isinstance(data, dict) else data
        titles = [it.get("title") for it in (body if isinstance(body, list) else [])]
        for t in ("A Test", "B Test", "C Test"):
            assert any(t == x for x in titles)

        # сортировки просто возвращают 200
        resp2 = self.client.get("/api/tests/?order_by=title")
        assert resp2.status_code == 200
        resp3 = self.client.get("/api/tests/?order_by=-title")
        assert resp3.status_code == 200

    def test_by_title_action_exact_and_partial(self):
        self.client.force_authenticate(user=self.admin)
        # отсутствие параметра title -> 400
        resp = self.client.get("/api/tests/by_title/")
        assert resp.status_code == 400

        # точное совпадение
        resp2 = self.client.get("/api/tests/by_title/?title=A Test&exact=true")
        assert resp2.status_code == 200
        data = resp2.json()
        body = data.get("results", data) if isinstance(data, dict) else data
        assert any(
            (t.get("title") == "A Test")
            for t in (body if isinstance(body, list) else [])
        )

        # частичное совпадение с пагинацией
        resp3 = self.client.get(
            "/api/tests/by_title/?title=Test&exact=false&page=1&page_size=2"
        )
        assert resp3.status_code == 200

    def test_start_submit_flow_student_and_teacher(self):
        # студент без прогресса не может начать тест
        self.client.force_authenticate(user=self.student)
        resp = self.client.post(f"/api/tests/{self.test_a.id}/start_test/")
        assert resp.status_code in (403, 404)

        # даём прогресс и начинаем
        UserLessonProgress.objects.create(
            user=self.student, lesson=self.lesson, is_completed=True
        )
        resp2 = self.client.post(f"/api/tests/{self.test_a.id}/start_test/")
        assert resp2.status_code == 201
        attempt = resp2.json()
        att_id = attempt.get("id")
        assert att_id is not None

        # отправляем правильный ответ
        payload = {
            "answers": [
                {"question_id": self.question.id, "chosen_answer_ids": [self.ans_ok.id]}
            ]
        }
        resp3 = self.client.post(
            f"/api/tests/{self.test_a.id}/submit_test/", data=payload, format="json"
        )
        assert resp3.status_code == 200

        # проверяем, что попытка помечена завершённой и у неё есть score
        qa = QuizAttempt.objects.get(id=att_id)
        assert qa.is_completed
        assert qa.score >= 0

        # преподаватель может стартовать тест без прогресса
        self.client.force_authenticate(user=self.teacher2)
        resp_t = self.client.post(f"/api/tests/{self.test_a.id}/start_test/")
        assert resp_t.status_code == 201

    def test_submit_without_active_attempt_returns_400(self):
        # студент с доступом, но без активной попытки -> 400/403
        UserLessonProgress.objects.create(
            user=self.student, lesson=self.lesson, is_completed=True
        )
        self.client.force_authenticate(user=self.student)
        payload = {
            "answers": [
                {"question_id": self.question.id, "chosen_answer_ids": [self.ans_ok.id]}
            ]
        }
        resp = self.client.post(
            f"/api/tests/{self.test_a.id}/submit_test/", data=payload, format="json"
        )
        assert resp.status_code in (400, 403)

    def test_get_current_attempt_variations(self):
        # активная попытка
        active = QuizAttempt.objects.create(
            user=self.student, quiz=self.test_a, is_completed=False
        )
        self.client.force_authenticate(user=self.student)
        resp = self.client.get(f"/api/tests/{self.test_a.id}/get_current_attempt/")
        assert resp.status_code in (200, 403, 404)
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("id") == active.id

        # преподаватель -> 404
        self.client.force_authenticate(user=self.teacher)
        resp2 = self.client.get(f"/api/tests/{self.test_a.id}/get_current_attempt/")
        assert resp2.status_code == 404

    def test_update_and_delete_permissions(self):
        # владелец может удалить
        t = Test.objects.create(
            title="DeleteTest",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.delete(f"/api/tests/{t.id}/")
        assert resp.status_code in (204, 200)
        self.assertFalse(Test.objects.filter(id=t.id).exists())

        # не-владелец не может удалить
        t2 = Test.objects.create(
            title="DeleteTest2",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        other = User.objects.create_user(email="other_cov@a.aa", password="pw")
        self.client.force_authenticate(user=other)
        resp2 = self.client.delete(f"/api/tests/{t2.id}/")
        assert resp2.status_code in (403, 404)

    def test_questionviewset_permissions_and_queryset(self):
        Question.objects.create(test=self.test_a, text="TchrQ", question_order=1)
        Question.objects.create(test=self.test_c, text="ModQ", question_order=1)

        # преподаватель видит вопросы своих дисциплин
        self.client.force_authenticate(user=self.teacher)
        resp_teacher_list = self.client.get("/api/questions/")
        self.assertEqual(resp_teacher_list.status_code, 200)
        titles = [q["text"] for q in resp_teacher_list.json()["results"]]
        self.assertIn("TchrQ", titles)
        self.assertIn("ModQ", titles)

    def test_answerviewset_permissions_and_queryset(self):
        ans_teacher = Answer.objects.create(
            question=self.question, text="TchrAns", is_correct=True
        )
        # преподаватель видит ответы своих дисциплин
        self.client.force_authenticate(user=self.teacher)
        resp_teacher_list = self.client.get("/api/answers/")
        self.assertEqual(resp_teacher_list.status_code, 200)
        texts = [a["text"] for a in resp_teacher_list.json()["results"]]
        self.assertIn("TchrAns", texts)

        # студент не видит ответы по умолчанию
        self.client.force_authenticate(user=self.student)
        resp_student_list = self.client.get("/api/answers/")
        self.assertEqual(resp_student_list.status_code, 200)
        self.assertEqual(len(resp_student_list.json()["results"]), 0)

        # админ может создать ответ
        self.client.force_authenticate(user=self.admin)
        resp_admin_create = self.client.post(
            "/api/answers/",
            data={
                "question": self.question.id,
                "text": "AdminCreatedA",
                "is_correct": False,
            },
            format="json",
        )
        self.assertEqual(resp_admin_create.status_code, 201)

        # другой учитель не может удалить ответ другого учителя
        self.client.force_authenticate(user=self.teacher2)
        resp_other_teacher_delete = self.client.delete(
            f"/api/answers/{ans_teacher.id}/"
        )
        self.assertEqual(resp_other_teacher_delete.status_code, 403)
