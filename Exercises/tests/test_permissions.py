from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from Disciplines.models import Discipline
from Exercises.models import Answer, Question, Test
from Exercises.permissions import IsTestOwnerOrAdminOrModerator
from Lessons.models import Lesson

User = get_user_model()


class PermissionsTests(TestCase):
    """Тесты для IsTestOwnerOrAdminOrModerator."""

    def setUp(self):
        for name in ["teacher", "student", "admin", "moderator"]:
            Group.objects.get_or_create(name=name)
        self.owner = User.objects.create_user(email="owner@example.com", password="pw")
        self.teacher_group = Group.objects.get(name="teacher")
        self.owner.groups.add(self.teacher_group)
        self.other = User.objects.create_user(email="other@example.com", password="pw")
        self.mod = User.objects.create_user(email="mod@example.com", password="pw")
        self.mod.groups.add(Group.objects.get(name="moderator"))

        self.discipline = Discipline.objects.create(
            title="DP", description="d", owner=self.owner
        )
        self.lesson = Lesson.objects.create(
            title="LL", discipline=self.discipline, owner=self.owner, lesson_order=1
        )
        self.test = Test.objects.create(
            title="TT", discipline=self.discipline, lesson=self.lesson, owner=self.owner
        )
        self.question = Question.objects.create(
            test=self.test, text="Q", question_order=1, is_multiple=False
        )
        self.answer = Answer.objects.create(
            question=self.question, text="A", is_correct=True
        )
        self.permission = IsTestOwnerOrAdminOrModerator()

    def test_has_permission_create(self):
        request = type("R", (), {"method": "POST", "user": self.owner})()
        # Владелец (учитель) может создавать
        self.assertTrue(self.permission.has_permission(request, None))
        # Обычный пользователь без роли teacher/admin/moderator не может
        request = type("R", (), {"method": "POST", "user": self.other})()
        self.assertFalse(self.permission.has_permission(request, None))

    def test_has_object_permission_owner(self):
        request = type("R", (), {"method": "PUT", "user": self.owner})()
        self.assertTrue(self.permission.has_object_permission(request, None, self.test))
        request = type("R", (), {"method": "PUT", "user": self.other})()
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.test)
        )

    def test_has_object_permission_moderator(self):
        request = type("R", (), {"method": "DELETE", "user": self.mod})()
        self.assertTrue(self.permission.has_object_permission(request, None, self.test))
