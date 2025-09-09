from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Exercises.models import Test
from Lessons.models import Lesson

User = get_user_model()


class TestViewSetBranchTests(TestCase):
    """Проверяем разные ветки логики в представлениях тестов."""

    def setUp(self):
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)

        self.teacher = User.objects.create_user(
            email="branch_teacher@a.aa", password="pw"
        )
        self.teacher.groups.add(Group.objects.get(name="teacher"))
        self.student = User.objects.create_user(
            email="branch_student@a.aa", password="pw"
        )
        self.student.groups.add(Group.objects.get(name="student"))
        self.admin = User.objects.create_user(email="branch_admin@a.aa", password="pw")
        self.admin.groups.add(Group.objects.get(name="admin"))

        self.discipline = Discipline.objects.create(
            title="BRDisc", description="d", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="BRLesson",
            discipline=self.discipline,
            owner=self.teacher,
            lesson_order=1,
        )

        self.test_unique = Test.objects.create(
            title="Unique-Title-XYZ",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )

        self.client = APIClient()

    def test_retrieve_by_title_single_match_returns_200(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(f"/api/tests/{self.test_unique.title}/")
        # ожидаем 200 при однозначном совпадении title
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("id"), self.test_unique.id)

    def test_retrieve_by_title_multiple_with_id_param_returns_chosen(self):
        # создаём два теста с одинаковым title и уточняем через ?id=
        Test.objects.create(
            title="SameTitleX",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        t2 = Test.objects.create(
            title="SameTitleX",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(f"/api/tests/SameTitleX/?id={t2.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("id"), t2.id)

    def test_retrieve_slug_branch_calls_slug_lookup_if_meta_has_field(self):
        # ветка, где у Test есть поле slug -> проверяем попытку поиска по slug
        t = Test.objects.create(
            title="SlugTitle",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        slug_lookup_value = "my-special-slug"

        # подменяем Test._meta.get_field чтобы имитировать наличие поля slug
        with patch.object(Test._meta, "get_field", return_value=object()):
            orig_get = Test.objects.get

            def fake_get(*args, **kwargs):
                if "slug" in kwargs and kwargs["slug"] == slug_lookup_value:
                    return t
                return orig_get(*args, **kwargs)

            with patch.object(Test.objects, "get", side_effect=fake_get):
                self.client.force_authenticate(user=self.admin)
                resp = self.client.get(f"/api/tests/{slug_lookup_value}/")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json().get("id"), t.id)

    def test_submit_test_nonexistent_test_returns_404(self):
        self.client.force_authenticate(user=self.student)
        payload = {"answers": [{"question_id": 1, "chosen_answer_ids": [1]}]}
        resp = self.client.post(
            "/api/tests/999999/submit_test/", data=payload, format="json"
        )
        self.assertEqual(resp.status_code, 404)

    def test_start_test_nonexistent_returns_404(self):
        self.client.force_authenticate(user=self.student)
        resp = self.client.post("/api/tests/999999/start_test/")
        self.assertEqual(resp.status_code, 404)

    def test_get_current_attempt_without_attempt_and_no_access_returns_403_for_student(
        self,
    ):
        # студент без прогресса и попытки -> должен получить 403 или 404
        self.client.force_authenticate(user=self.student)
        resp = self.client.get(f"/api/tests/{self.test_unique.id}/get_current_attempt/")
        self.assertIn(resp.status_code, (403, 404))
        if resp.status_code == 403:
            self.assertIn("Доступ к этому тесту закрыт", str(resp.json()))

    def test_get_current_attempt_returns_404_for_admin_when_no_attempt(self):
        # админ без попытки -> 404
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(f"/api/tests/{self.test_unique.id}/get_current_attempt/")
        self.assertEqual(resp.status_code, 404)
