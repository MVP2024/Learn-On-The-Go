from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient, APITestCase

from Disciplines.models import Discipline
from Exercises.models import Test
from Lessons.models import Lesson

User = get_user_model()


class TeacherRelatedContentAPITests(APITestCase):
    """Функциональные тесты для Teachers.views. TeacherRelatedContentViewSet.

    Проверяем, что эндпоинты возвращают дисциплины/уроки/тесты только для текущего учителя
    и требуют соответствующих прав.
    """

    def setUp(self):
        # Создаём группы
        for g in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=g)

        # Пользователи
        self.teacher = User.objects.create_user(email="t_view@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))

        self.other_teacher = User.objects.create_user(email="other@a.aa", password="pw")
        self.other_teacher.groups.add(Group.objects.get(name="teacher"))

        self.student = User.objects.create_user(email="stud@a.aa", password="pw")
        self.student.groups.add(Group.objects.get(name="student"))

        # Содержимое
        self.disc1 = Discipline.objects.create(
            title="TDisc1", description="d", owner=self.teacher, slug="tdisc1"
        )
        self.disc2 = Discipline.objects.create(
            title="TDisc2", description="d", owner=self.other_teacher, slug="tdisc2"
        )
        self.lesson1 = Lesson.objects.create(
            title="L1",
            discipline=self.disc1,
            owner=self.teacher,
            lesson_order=1,
            video_url="http://ex",
        )
        self.lesson2 = Lesson.objects.create(
            title="L2",
            discipline=self.disc2,
            owner=self.other_teacher,
            lesson_order=1,
            video_url="http://ex",
        )
        self.test1 = Test.objects.create(
            title="Test1",
            discipline=self.disc1,
            lesson=self.lesson1,
            owner=self.teacher,
        )
        self.test2 = Test.objects.create(
            title="Test2",
            discipline=self.disc2,
            lesson=self.lesson2,
            owner=self.other_teacher,
        )

        self.client = APIClient()

    def test_my_disciplines_returns_only_owned(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get("/api/teacher-content/my_disciplines/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Должны присутствовать только дисциплины, где owner == teacher
        ids = {d.get("id") for d in data}
        self.assertIn(self.disc1.id, ids)
        self.assertNotIn(self.disc2.id, ids)

    def test_my_lessons_returns_only_owned(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get("/api/teacher-content/my_lessons/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = {lesson.get("id") for lesson in data}
        self.assertIn(self.lesson1.id, ids)
        self.assertNotIn(self.lesson2.id, ids)

    def test_my_tests_returns_only_owned(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get("/api/teacher-content/my_tests/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = {t.get("id") for t in data}
        self.assertIn(self.test1.id, ids)
        self.assertNotIn(self.test2.id, ids)

    def test_permissions_denied_for_non_teacher(self):
        self.client.force_authenticate(user=self.student)
        resp = self.client.get("/api/teacher-content/my_disciplines/")
        # Ожидаем 403 (permission classes require teacher role)
        self.assertIn(resp.status_code, (403, 401))
