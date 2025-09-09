from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from Disciplines.models import Discipline, Section
from Disciplines.views import SectionViewSet

factory = RequestFactory()


class SectionViewSetTests(TestCase):
    def setUp(self):
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)
        User = get_user_model()
        self.teacher1 = User.objects.create_user(email="t1_sec@a.aa", password="pw")
        self.teacher1.groups.add(Group.objects.get(name="teacher"))
        self.teacher2 = User.objects.create_user(email="t2_sec@a.aa", password="pw")
        self.teacher2.groups.add(Group.objects.get(name="teacher"))
        self.admin = User.objects.create_user(email="adm_sec@a.aa", password="pw")
        self.admin.groups.add(Group.objects.get(name="admin"))

        # две дисциплины, которые ведут разные преподаватели
        self.disc1 = Discipline.objects.create(
            title="DiscOne", description="d", owner=self.teacher1
        )
        self.disc2 = Discipline.objects.create(
            title="DiscTwo", description="d", owner=self.teacher2
        )

    def test_teacher_can_create_section_for_own_discipline(self):
        client = APIClient()
        client.force_authenticate(user=self.teacher1)
        payload = {
            "title": "Chapter 1",
            "section_order": 1,
            "discipline": self.disc1.slug,
        }
        resp = client.post("/api/sections/", data=payload, format="json")
        self.assertEqual(resp.status_code, 201)
        sec = Section.objects.get(title="Chapter 1")
        self.assertEqual(sec.discipline, self.disc1)

    def test_teacher_cannot_create_section_for_other_discipline(self):
        client = APIClient()
        client.force_authenticate(user=self.teacher1)
        payload = {
            "title": "Bad Chapter",
            "section_order": 1,
            "discipline": self.disc2.slug,
        }
        resp = client.post("/api/sections/", data=payload, format="json")
        # при выполнении функции perform_create возникает ошибка serializers.ValidationError
        # -> API должен возвращать 400
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Section.objects.filter(title="Bad Chapter").exists())

    def test_get_queryset_filter_by_id_and_slug(self):
        # создание разделов
        s1 = Section.objects.create(title="S1", section_order=1, discipline=self.disc1)
        s2 = Section.objects.create(title="S2", section_order=2, discipline=self.disc2)

        view = SectionViewSet()
        # нумерация фильтров
        req_num = factory.get(f"/api/sections/?discipline={self.disc1.id}")
        req_num.user = self.admin
        req_num.query_params = req_num.GET
        view.request = req_num
        qs_num = view.get_queryset()
        self.assertIn(s1, list(qs_num))
        self.assertNotIn(s2, list(qs_num))

        # slug фильтра
        req_slug = factory.get(f"/api/sections/?discipline={self.disc2.slug}")
        req_slug.user = self.admin
        req_slug.query_params = req_slug.GET
        view.request = req_slug
        qs_slug = view.get_queryset()
        self.assertIn(s2, list(qs_slug))
        self.assertNotIn(s1, list(qs_slug))
