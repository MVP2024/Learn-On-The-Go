from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import serializers

from Disciplines.models import Discipline
from Exercises.models import Test as QuizTest
from Lessons.models import Lesson
from utils.common_mixins import OwnerCreateMixin, TitleOrPkLookupMixin

User = get_user_model()


class _FakeSerializer:
    def __init__(self, validated_data):
        self.validated_data = validated_data
        self.saved_with = None

    def save(self, **kwargs):
        # просто запомним owner и вернём dummy
        self.saved_with = kwargs
        return kwargs


class OwnerCreateMixinPerformCreateTests(TestCase):
    """Проверяем разные ветки perform_create из OwnerCreateMixin."""

    def setUp(self):
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)
        self.teacher = User.objects.create_user(email="oc_teacher@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))
        self.other_teacher = User.objects.create_user(
            email="oc_other@a.aa", password="pw"
        )
        self.other_teacher.groups.add(Group.objects.get(name="teacher"))
        self.admin = User.objects.create_user(
            email="oc_admin@a.aa", password="pw", is_superuser=True
        )
        self.student = User.objects.create_user(email="oc_student@a.aa", password="pw")

        self.disc_owned = Discipline.objects.create(
            title="Down", description="d", owner=self.teacher
        )
        self.disc_other = Discipline.objects.create(
            title="Dother", description="d", owner=self.other_teacher
        )
        self.disc_none = Discipline.objects.create(title="Dnone", description="d")

        self.lesson_owned = Lesson.objects.create(
            title="Lown",
            discipline=self.disc_owned,
            owner=self.teacher,
            lesson_order=1,
            video_url="http://ex",
        )
        self.lesson_other = Lesson.objects.create(
            title="Lother",
            discipline=self.disc_other,
            owner=self.other_teacher,
            lesson_order=1,
            video_url="http://ex",
        )

    @staticmethod
    def _make_mixin_with_user(user):
        m = OwnerCreateMixin()
        m.request = type("R", (), {"user": user})()
        return m

    def test_teacher_creates_for_own_discipline_and_lesson(self):
        mix = self._make_mixin_with_user(self.teacher)
        ser = _FakeSerializer(
            {"discipline": self.disc_owned, "lesson": self.lesson_owned}
        )
        mix.perform_create(ser)
        self.assertEqual(ser.saved_with.get("owner"), self.teacher)

    def test_teacher_cannot_create_for_other_teacher_discipline(self):
        mix = self._make_mixin_with_user(self.teacher)
        ser = _FakeSerializer({"discipline": self.disc_other})
        with self.assertRaises(serializers.ValidationError):
            mix.perform_create(ser)

    def test_moderator_creates_without_owner_for_unowned_or_own(self):
        moderator = User.objects.create_user(email="modu@a.aa", password="pw")
        moderator.groups.add(Group.objects.get(name="moderator"))
        mix = self._make_mixin_with_user(moderator)
        # никому не принадлежащая дисциплина-> ok
        ser1 = _FakeSerializer({"discipline": self.disc_none})
        mix.perform_create(ser1)
        self.assertIsNone(ser1.saved_with.get("owner"))
        # собственный урок, где владелец != модератор -> модератор может создавать только для тех, у кого нет аккаунта,
        # или для себя; для других аккаунтов должна выдаваться ошибка
        ser2 = _FakeSerializer({"discipline": self.disc_other})
        with self.assertRaises(serializers.ValidationError):
            mix.perform_create(ser2)

    def test_admin_or_super_can_create_owner_none(self):
        mix = self._make_mixin_with_user(self.admin)
        ser = _FakeSerializer({"discipline": self.disc_other})
        mix.perform_create(ser)
        self.assertIn("owner", ser.saved_with)
        # Владелец не указан в настройках администратора
        self.assertIsNone(ser.saved_with.get("owner"))

    def test_unauthenticated_raises(self):
        mix = OwnerCreateMixin()
        mix.request = type("R", (), {"user": None})()
        ser = _FakeSerializer({"discipline": None})
        with self.assertRaises(serializers.ValidationError):
            mix.perform_create(ser)


class TitleOrPkLookupMixinMultipleMatchesTests(TestCase):
    """Проверяем поведение при множественных совпадениях title в TitleOrPkLookupMixin."""

    def setUp(self):
        self.user = User.objects.create_user(email="tpk@a.aa", password="pw")
        self.t = QuizTest.objects.create(
            title="SameTitle",
            discipline=Discipline.objects.create(title="X", description="d"),
            lesson=None,
            owner=self.user,
        )
        self.t2 = QuizTest.objects.create(
            title="SameTitle",
            discipline=Discipline.objects.create(title="Y", description="d"),
            lesson=None,
            owner=self.user,
        )

    def test_multiple_matches_without_id_raises(self):
        class Dummy(TitleOrPkLookupMixin):
            lookup_field = "pk"

            def get_queryset(self):
                return QuizTest.objects

            def filter_queryset(self, qs):
                return qs

            def check_object_permissions(self, request, obj):
                return True

        d = Dummy()
        d.request = type("R", (), {"user": self.user, "query_params": {}})()
        d.kwargs = {"pk": "SameTitle"}
        with self.assertRaises(serializers.ValidationError):
            d.get_object()

    def test_multiple_matches_with_bad_id_param_raises(self):
        class Dummy(TitleOrPkLookupMixin):
            lookup_field = "pk"

            def get_queryset(self):
                return QuizTest.objects

            def filter_queryset(self, qs):
                return qs

            def check_object_permissions(self, request, obj):
                return True

        d = Dummy()
        d.request = type("R", (), {"user": self.user, "query_params": {"id": "abc"}})()
        d.kwargs = {"pk": "SameTitle"}
        with self.assertRaises(serializers.ValidationError):
            d.get_object()

    def test_multiple_matches_with_id_param_selects_correct(self):
        class Dummy(TitleOrPkLookupMixin):
            lookup_field = "pk"

            def get_queryset(self):
                return QuizTest.objects

            def filter_queryset(self, qs):
                return qs

            def check_object_permissions(self, request, obj):
                return True

        d = Dummy()
        d.request = type(
            "R", (), {"user": self.user, "query_params": {"id": str(self.t2.pk)}}
        )()
        d.kwargs = {"pk": "SameTitle"}
        obj = d.get_object()
        self.assertEqual(obj.pk, self.t2.pk)
