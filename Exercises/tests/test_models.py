from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.test import TestCase

from Disciplines.models import Discipline
from Exercises.models import Answer, Choice, Question, QuizAttempt, Test
from Lessons.models import Lesson

User = get_user_model()


class ModelsBasicTests(TestCase):
    """Проверяем строковые представления и поведение моделей."""

    def setUp(self):
        self.teacher = User.objects.create_user(email="t@example.com", password="pw")
        self.discipline = Discipline.objects.create(
            title="D1", description="d", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="L1", discipline=self.discipline, owner=self.teacher, lesson_order=1
        )
        self.test = Test.objects.create(
            title="T1",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        self.question = Question.objects.create(
            test=self.test, text="Q?", question_order=1, is_multiple=False
        )
        self.ans1 = Answer.objects.create(
            question=self.question, text="A1", is_correct=True
        )
        self.ans2 = Answer.objects.create(
            question=self.question, text="A2", is_correct=False
        )
        self.student = User.objects.create_user(email="s@example.com", password="pw")
        self.attempt = QuizAttempt.objects.create(user=self.student, quiz=self.test)

    def test_str_methods(self):
        self.assertIn("T1", str(self.test))
        self.assertIn("Q?", str(self.question))
        self.assertIn("A1", str(self.ans1))
        self.assertIn(self.student.email, str(self.attempt))

    def test_choice_unique_constraint(self):
        # создаём выбор; повторный такой же вызов должен упасть с IntegrityError
        Choice.objects.create(
            user=self.student,
            question=self.question,
            answer=self.ans1,
            quiz_attempt=self.attempt,
        )
        with self.assertRaises(IntegrityError):
            Choice.objects.create(
                user=self.student,
                question=self.question,
                answer=self.ans1,
                quiz_attempt=self.attempt,
            )
