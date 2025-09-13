from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from Disciplines.models import Discipline
from Exercises.models import Test
from Lessons.models import Lesson, UserLessonProgress

User = get_user_model()


class ViewsUtilsTests(TestCase):
    """Проверяем _accessible_tests_for_student"""

    def setUp(self):
        for g in ["teacher", "student", "admin", "moderator"]:
            Group.objects.get_or_create(name=g)
        self.teacher = User.objects.create_user(email="tv@example.com", password="pw")
        self.student = User.objects.create_user(email="sv@example.com", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))
        self.student.groups.add(Group.objects.get(name="student"))

        self.discipline = Discipline.objects.create(
            title="DiscA", description="d", owner=self.teacher
        )
        # Два урока
        self.l1 = Lesson.objects.create(
            title="L1", discipline=self.discipline, owner=self.teacher, lesson_order=1
        )
        self.l2 = Lesson.objects.create(
            title="L2", discipline=self.discipline, owner=self.teacher, lesson_order=2
        )
        # Тест, привязанный к первому уроку
        self.t_lesson = Test.objects.create(
            title="TL", discipline=self.discipline, lesson=self.l1, owner=self.teacher
        )
        # Тест, не привязанный к уроку, требует полного прохождения дисциплины
        self.t_disc = Test.objects.create(
            title="TD", discipline=self.discipline, lesson=None, owner=self.teacher
        )

    def test_no_progress_no_access(self):
        from Exercises.views import _accessible_tests_for_student

        qs = _accessible_tests_for_student(self.student)
        self.assertFalse(qs.filter(pk=self.t_lesson.pk).exists())
        self.assertFalse(qs.filter(pk=self.t_disc.pk).exists())

    def test_after_lesson_completion_has_access(self):
        UserLessonProgress.objects.create(
            user=self.student, lesson=self.l1, is_completed=True
        )
        from Exercises.views import _accessible_tests_for_student

        qs = _accessible_tests_for_student(self.student)
        self.assertTrue(qs.filter(pk=self.t_lesson.pk).exists())

    def test_after_all_lessons_completed_disc_access(self):
        UserLessonProgress.objects.create(
            user=self.student, lesson=self.l1, is_completed=True
        )
        UserLessonProgress.objects.create(
            user=self.student, lesson=self.l2, is_completed=True
        )
        from Exercises.views import _accessible_tests_for_student

        qs = _accessible_tests_for_student(self.student)
        self.assertTrue(qs.filter(pk=self.t_disc.pk).exists())
