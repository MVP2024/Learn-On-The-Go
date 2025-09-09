from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient, APIRequestFactory, APITestCase

from Disciplines.models import Discipline
from Lessons.models import Lesson, UserLessonProgress
from Lessons.views import LessonViewSet

User = get_user_model()


class LessonViewSetTests(APITestCase):
    """Функциональные тесты для основных действий LessonViewSet."""

    def setUp(self):
        for g in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=g)

        self.teacher = User.objects.create_user(email="lv_teacher@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))

        self.other_teacher = User.objects.create_user(
            email="lv_other@a.aa", password="pw"
        )
        self.other_teacher.groups.add(Group.objects.get(name="teacher"))

        self.student = User.objects.create_user(email="lv_student@a.aa", password="pw")
        self.student.groups.add(Group.objects.get(name="student"))

        self.admin = User.objects.create_user(
            email="lv_admin@a.aa", password="pw", is_superuser=True
        )
        self.admin.groups.add(Group.objects.get(name="admin"))

        # дисциплины
        self.disc = Discipline.objects.create(
            title="LV Disc", description="d", owner=self.teacher, slug="lv_disc"
        )
        self.other_disc = Discipline.objects.create(
            title="Other Disc",
            description="d",
            owner=self.other_teacher,
            slug="other_disc",
        )

        self.client = APIClient()
        self.factory = APIRequestFactory()

    def test_create_lesson_teacher_success(self):
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "title": "CreateLesson",
            "discipline": self.disc.slug,
            "video_url": "https://ok.example.com/video",
            "lesson_order": 1,
        }
        resp = self.client.post("/api/lessons/", data=payload, format="json")
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body.get("owner"), self.teacher.id)

    def test_create_lesson_teacher_for_other_discipline_forbidden(self):
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "title": "BadCreate",
            "discipline": self.other_disc.slug,
            "video_url": "https://ok.example.com/video",
            "lesson_order": 1,
        }
        resp = self.client.post("/api/lessons/", data=payload, format="json")
        # OwnerCreateMixin поднимает ValidationError -> DRF вернёт 400
        self.assertIn(resp.status_code, (400, 403))

    def test_create_lesson_student_forbidden(self):
        self.client.force_authenticate(user=self.student)
        payload = {
            "title": "StudentCreate",
            "discipline": self.disc.slug,
            "video_url": "https://ok.example.com/video",
            "lesson_order": 1,
        }
        resp = self.client.post("/api/lessons/", data=payload, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_update_progress_student_and_invalid(self):
        lesson = Lesson.objects.create(
            title="ProgLesson",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="https://example.com/v",
        )
        # студент может обновлять прогресс
        self.client.force_authenticate(user=self.student)
        resp = self.client.post(
            f"/api/lessons/{lesson.id}/update_progress/",
            data={"watched_duration": 50, "is_completed": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("watched_duration"), 50)
        self.assertTrue(data.get("is_completed"))

        # неверное watched_duration -> 400
        resp2 = self.client.post(
            f"/api/lessons/{lesson.id}/update_progress/",
            data={"watched_duration": "abc"},
            format="json",
        )
        self.assertEqual(resp2.status_code, 400)

    def test_update_progress_teacher_forbidden(self):
        lesson = Lesson.objects.create(
            title="ProgLesson2",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="https://example.com/v",
        )
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.post(
            f"/api/lessons/{lesson.id}/update_progress/",
            data={"watched_duration": 10},
            format="json",
        )
        # Преподаватель не должен обновлять прогресс студента -> ожидается 403/404
        self.assertIn(resp.status_code, (403, 404))

    def test_get_progress_not_found_and_found(self):
        lesson = Lesson.objects.create(
            title="GP",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="https://example.com/v",
        )
        self.client.force_authenticate(user=self.student)
        resp = self.client.get(f"/api/lessons/{lesson.id}/get_progress/")
        self.assertEqual(resp.status_code, 404)
        # создаём прогресс и запрашиваем
        prog = UserLessonProgress.objects.create(
            user=self.student, lesson=lesson, is_completed=False, watched_duration=15
        )
        resp2 = self.client.get(f"/api/lessons/{lesson.id}/get_progress/")
        self.assertEqual(resp2.status_code, 200)
        body = resp2.json()
        self.assertEqual(body.get("watched_duration"), prog.watched_duration)

    def test_by_title_action(self):
        Lesson.objects.create(
            title="FindMe",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="https://example.com/v",
        )
        Lesson.objects.create(
            title="FindMe",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=2,
            video_url="https://example.com/v",
        )
        self.client.force_authenticate(user=self.admin)
        # отсутствие title -> 400
        resp = self.client.get("/api/lessons/by_title/")
        self.assertEqual(resp.status_code, 400)
        # точное совпадение
        resp2 = self.client.get("/api/lessons/by_title/?title=FindMe&exact=true")
        self.assertEqual(resp2.status_code, 200)
        # частичное совпадение с пагинацией
        resp3 = self.client.get(
            "/api/lessons/by_title/?title=Find&exact=false&page=1&page_size=1"
        )
        self.assertEqual(resp3.status_code, 200)

    def test_get_queryset_ordering_teacher_and_admin(self):
        Lesson.objects.create(
            title="A",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=2,
            video_url="https://example.com/v",
        )
        Lesson.objects.create(
            title="B",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="https://example.com/v",
        )
        view = LessonViewSet()
        # teacher видит свои уроки
        req = self.factory.get("/api/lessons/")
        req.user = self.teacher
        req.query_params = req.GET
        view.request = req
        qs = view.get_queryset()
        self.assertTrue(qs.exists())
        # admin видит все уроки
        req2 = self.factory.get("/api/lessons/")
        req2.user = self.admin
        req2.query_params = req2.GET
        view.request = req2
        qs2 = view.get_queryset()
        self.assertTrue(qs2.count() >= qs.count())
