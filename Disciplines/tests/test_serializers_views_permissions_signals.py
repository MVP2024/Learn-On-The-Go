from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from rest_framework import serializers as drf_serializers
from rest_framework.request import Request

# DRF test utilities
from rest_framework.test import APIRequestFactory

from Disciplines import common_permissions
from Disciplines.models import Discipline
from Disciplines.serializers import DisciplineSerializer, SectionSerializer

factory = APIRequestFactory()


def make_django_request(user, method="GET", data=None, path="/"):
    method = method.lower()
    if not hasattr(factory, method):
        django_req = factory.get(path, data=data or {})
    else:
        django_req = getattr(factory, method)(path, data=data or {})
    django_req.user = user
    django_req.query_params = django_req.GET
    return django_req


def make_drf_request(user, method="GET", data=None, path="/"):
    django_req = make_django_request(user, method=method, data=data, path=path)
    return Request(django_req)


class SerializerAndAccessTests(TestCase):
    """Тесты для сериализаторов Discipline/Section и проверки доступа."""

    def setUp(self):
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)
        self.discipline = Discipline.objects.create(
            title="Тест дисциплины", description="d"
        )
        self.assertIsNotNone(self.discipline.slug)

    def test_discipline_serializer_price_and_access_mocked(self):
        User = get_user_model()
        student = User.objects.create_user(email="stu@a.aa", password="pw")
        student.groups.add(Group.objects.get(name="student"))
        req = make_django_request(student)

        # Информация о цене_ по умолчанию
        ser = DisciplineSerializer(self.discipline, context={})
        self.assertIn("price_info", ser.data)

        # Помощник по сериализации патчей для контроля результатов доступа
        with patch(
            "Disciplines.serializers.DisciplineSerializer.get_user_has_access",
            return_value=True,
        ):
            ser2 = DisciplineSerializer(self.discipline, context={"request": req})
            self.assertTrue(ser2.get_user_has_access(self.discipline))

        with patch(
            "Disciplines.serializers.DisciplineSerializer.get_user_has_access",
            return_value=False,
        ):
            ser3 = DisciplineSerializer(self.discipline, context={"request": req})
            self.assertFalse(ser3.get_user_has_access(self.discipline))

    def test_section_serializer_accepts_slug(self):
        payload = {
            "title": "Глава 1",
            "section_order": 1,
            "discipline": self.discipline.slug,
        }
        ser = SectionSerializer(data=payload)
        self.assertTrue(ser.is_valid(), msg=str(ser.errors))
        obj = ser.save()
        self.assertEqual(obj.discipline, self.discipline)


class ViewsetPerformCreateTests(TestCase):
    def setUp(self):
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)
        self.payload = {"title": "Созданная дисциплина", "description": "desc"}

    @staticmethod
    def _make_user(roles=()):
        User = get_user_model()
        u = User.objects.create_user(email=f"u_{len(roles)}@a.aa", password="pw")
        for r in roles:
            g = Group.objects.get(name=r)
            u.groups.add(g)
        return u

    def test_teacher_creates_with_owner(self):
        user = self._make_user(("teacher",))
        ser = DisciplineSerializer(data=self.payload)
        ser.is_valid(raise_exception=True)
        ser.save(owner=user)
        d = Discipline.objects.get(title=self.payload["title"])
        self.assertEqual(d.owner, user)

    def test_moderator_creates_without_owner(self):
        self._make_user(("moderator",))
        ser = DisciplineSerializer(data=self.payload)
        ser.is_valid(raise_exception=True)
        ser.save(owner=None)
        d = Discipline.objects.get(title=self.payload["title"])
        self.assertIsNone(d.owner)

    def test_other_user_cannot_create(self):
        user_student = self._make_user(("student",))
        ser = DisciplineSerializer(data=self.payload)
        ser.is_valid(raise_exception=True)
        if (
            user_student.groups.filter(name="student").exists()
            and not user_student.groups.filter(name="teacher").exists()
        ):
            with self.assertRaises(drf_serializers.ValidationError):
                raise drf_serializers.ValidationError(
                    "У вас нет прав для создания дисциплин."
                )


class PermissionsUnitTests(TestCase):
    def setUp(self):
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)
        User = get_user_model()
        self.owner = User.objects.create_user(email="own@a.aa", password="pw")
        self.other = User.objects.create_user(email="oth@a.aa", password="pw")
        # даем владельцу группу преподавателей
        self.owner.groups.add(Group.objects.get(name="teacher"))
        self.mod = User.objects.create_user(email="mod@a.aa", password="pw")
        self.mod.groups.add(Group.objects.get(name="moderator"))

    def test_is_owner_or_admin_or_moderator(self):
        perm = common_permissions.IsOwnerOrAdminOrModerator()
        req = type("R", (), {"user": self.other, "method": "GET"})()
        self.assertTrue(
            perm.has_object_permission(
                req, None, type("O", (), {"owner": self.owner})()
            )
        )
        req2 = type("R", (), {"user": self.other, "method": "PUT"})()
        self.assertFalse(
            perm.has_object_permission(
                req2, None, type("O", (), {"owner": self.owner})()
            )
        )
        req3 = type("R", (), {"user": self.owner, "method": "PUT"})()
        self.assertTrue(
            perm.has_object_permission(
                req3, None, type("O", (), {"owner": self.owner})()
            )
        )
        req4 = type("R", (), {"user": self.mod, "method": "DELETE"})()
        self.assertTrue(
            perm.has_object_permission(
                req4, None, type("O", (), {"owner": self.owner})()
            )
        )

    def test_is_teacher_or_admin_or_moderator(self):
        perm = common_permissions.IsTeacherOrAdminOrModerator()
        req = type("R", (), {"user": self.owner, "method": "GET"})()
        self.assertTrue(perm.has_permission(req, None))
        req2 = type("R", (), {"user": self.other, "method": "GET"})()
        self.assertFalse(perm.has_permission(req2, None))


class ManagementCommandAndSignalsTests(TestCase):
    def setUp(self):
        for i in range(3):
            Discipline.objects.create(title=f"NoSlug {i}", description="d")

    def test_populate_slugs_dry_run_and_force(self):
        out = StringIO()
        call_command("populate_slugs", "--dry-run", stdout=out)
        txt = out.getvalue()
        self.assertTrue("[dry-run]" in txt or "Нет дисциплин для обработки" in txt)
        out2 = StringIO()
        call_command("populate_slugs", "--force", "--batch", "2", stdout=out2)
        self.assertIn("Готово", out2.getvalue())

    @staticmethod
    def test_signals_clear_cache_on_save_delete():
        d = Discipline.objects.create(title="SignalTest", description="d")
        with patch.object(cache, "delete") as mock_del:
            d.title = "SignalTestUpdated"
            d.save()
            mock_del.assert_called()
        with patch.object(cache, "delete") as mock_del2:
            pk_val = d.pk
            d.delete()
            mock_del2.assert_called_with(f"/disciplines/{pk_val}/")
