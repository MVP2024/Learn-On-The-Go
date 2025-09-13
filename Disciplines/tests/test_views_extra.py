from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline
from Disciplines.views import DisciplineViewSet

factory = RequestFactory()


class DisciplineViewSetExtraTests(TestCase):
    def setUp(self):
        # Убеждаемся, что группы существуют
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)
        User = get_user_model()
        self.teacher = User.objects.create_user(email="t_extra@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))
        self.moderator = User.objects.create_user(email="mod_extra@a.aa", password="pw")
        self.moderator.groups.add(Group.objects.get(name="moderator"))
        self.student = User.objects.create_user(email="stu_extra@a.aa", password="pw")
        self.student.groups.add(Group.objects.get(name="student"))
        self.admin = User.objects.create_user(email="adm_extra@a.aa", password="pw")
        self.admin.groups.add(Group.objects.get(name="admin"))

        Discipline.objects.create(title="AlphaOrd", description="d", owner=self.teacher)
        Discipline.objects.create(title="BetaOrd", description="d")
        Discipline.objects.create(title="GammaOrd", description="d")

    def test_create_as_teacher_sets_owner(self):
        client = APIClient()
        client.force_authenticate(user=self.teacher)
        payload = {"title": "CreatedByTeacher", "description": "desc"}
        resp = client.post("/api/disciplines/", data=payload, format="json")
        self.assertEqual(resp.status_code, 201)
        d = Discipline.objects.get(title="CreatedByTeacher")
        self.assertIsNotNone(d)
        self.assertEqual(d.owner, self.teacher)

    def test_create_as_moderator_owner_none(self):
        client = APIClient()
        client.force_authenticate(user=self.moderator)
        payload = {"title": "CreatedByMod", "description": "desc"}
        resp = client.post("/api/disciplines/", data=payload, format="json")
        self.assertEqual(resp.status_code, 201)
        d = Discipline.objects.get(title="CreatedByMod")
        # Модераторы создают контент без указания владельца в соответствии с perform_create
        self.assertIsNone(d.owner)

    def test_create_as_student_forbidden(self):
        client = APIClient()
        client.force_authenticate(user=self.student)
        payload = {"title": "CreatedByStudent", "description": "desc"}
        resp = client.post("/api/disciplines/", data=payload, format="json")
        # Студенту не разрешено создавать, ожидается ошибка 403 «Запрещено» или ошибка проверки
        self.assertIn(resp.status_code, (403, 400))
        self.assertFalse(Discipline.objects.filter(title="CreatedByStudent").exists())

    def test_get_queryset_ordering_variants(self):
        view = DisciplineViewSet()
        req = factory.get("/api/disciplines/", data={})
        req.user = self.admin
        req.query_params = req.GET
        view.request = req
        qs_default = view.get_queryset()
        titles = [d.title for d in qs_default]
        for expected in ("AlphaOrd", "BetaOrd", "GammaOrd"):
            self.assertIn(expected, titles)

        req2 = factory.get("/api/disciplines/?order_by=title")
        req2.user = self.admin
        req2.query_params = req2.GET
        view.request = req2
        qs_t = view.get_queryset()
        titles_t = [d.title for d in qs_t]
        self.assertEqual(titles_t[:3], sorted(titles_t)[:3])

        req3 = factory.get("/api/disciplines/?order_by=-title")
        req3.user = self.admin
        req3.query_params = req3.GET
        view.request = req3
        qs_dt = view.get_queryset()
        titles_dt = [d.title for d in qs_dt]
        self.assertEqual(titles_dt[:3], sorted(titles_dt, reverse=True)[:3])

        client = APIClient()
        client.force_authenticate(user=self.admin)
        resp = client.get(
            "/api/disciplines/by_title/?title=SearchMe&exact=false&page=1&page_size=2"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        if isinstance(data, dict):
            self.assertIn("results", data)
            self.assertLessEqual(len(data.get("results", [])), 2)
        else:
            self.assertLessEqual(len(data), 2)
