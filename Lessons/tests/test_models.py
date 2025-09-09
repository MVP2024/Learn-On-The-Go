from django.contrib.auth import get_user_model
from django.test import TestCase

from Disciplines.models import Discipline
from Lessons.models import Lesson, UserLessonProgress

User = get_user_model()


class LessonModelsTests(TestCase):
    """Тесты поведения и представления моделей Lesson и UserLessonProgress."""

    def setUp(self):
        self.teacher = User.objects.create_user(email="lm_teacher@a.aa", password="pw")
        self.disc = Discipline.objects.create(
            title="LMDisc", description="d", owner=self.teacher, slug="lm_disc"
        )

    def test_lesson_str_and_ordering(self):
        l1 = Lesson.objects.create(
            title="L One",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=2,
            video_url="http://ex",
        )
        Lesson.objects.create(
            title="L Two",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="http://ex",
        )
        self.assertIn("L One", str(l1))
        # Сортировка Meta: по дисциплине, разделу, lesson_order -> l2 должен идти перед l1
        qs = list(Lesson.objects.filter(discipline=self.disc).order_by("lesson_order"))
        self.assertEqual(qs[0].lesson_order, 1)

    def test_userlessonprogress_unique_constraint(self):
        student = User.objects.create_user(email="stu_lm@a.aa", password="pw")
        lesson = Lesson.objects.create(
            title="UniqueTest",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="http://ex",
        )
        UserLessonProgress.objects.create(
            user=student, lesson=lesson, is_completed=False
        )
        # повторная попытка создать прогресс для того же user+lesson должна упасть
        with self.assertRaises(Exception):
            UserLessonProgress.objects.create(
                user=student, lesson=lesson, is_completed=False
            )

    def test_userlessonprogress_str(self):
        student = User.objects.create_user(email="stu2_lm@a.aa", password="pw")
        lesson = Lesson.objects.create(
            title="StrTest",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="http://ex",
        )
        prog = UserLessonProgress.objects.create(
            user=student, lesson=lesson, is_completed=True
        )
        self.assertIn(student.email, str(prog))
        self.assertIn(lesson.title, str(prog))
