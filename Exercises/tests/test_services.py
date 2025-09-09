from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import serializers

from Disciplines.models import Discipline
from Exercises.models import Answer, Choice, Question, QuizAttempt, Test
from Exercises.services import QuizAttemptService
from Lessons.models import Lesson

User = get_user_model()


class ServicesTests(TestCase):
    """Тестируем логику подсчёта и submit_test_attempt."""

    def setUp(self):
        self.teacher = User.objects.create_user(email="t2@example.com", password="pw")
        self.student = User.objects.create_user(email="s2@example.com", password="pw")
        self.discipline = Discipline.objects.create(
            title="D2", description="d", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="L2", discipline=self.discipline, owner=self.teacher, lesson_order=1
        )
        self.test = Test.objects.create(
            title="T2",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )

        # Вопрос с одиночным выбором
        self.q1 = Question.objects.create(
            test=self.test, text="1+1", question_order=1, is_multiple=False
        )
        self.a1 = Answer.objects.create(question=self.q1, text="2", is_correct=True)
        self.a2 = Answer.objects.create(question=self.q1, text="3", is_correct=False)

        # Вопрос с множественным выбором
        self.q2 = Question.objects.create(
            test=self.test, text="Выбери два", question_order=2, is_multiple=True
        )
        self.b1 = Answer.objects.create(question=self.q2, text="A", is_correct=True)
        self.b2 = Answer.objects.create(question=self.q2, text="B", is_correct=True)
        self.b3 = Answer.objects.create(question=self.q2, text="C", is_correct=False)

        self.attempt = QuizAttempt.objects.create(user=self.student, quiz=self.test)

    def test_calculate_score_single_and_multiple(self):
        # Для q1 правильный выбор
        Choice.objects.create(
            user=self.student,
            question=self.q1,
            answer=self.a1,
            quiz_attempt=self.attempt,
        )
        # Для q2 выбраны оба правильных
        Choice.objects.create(
            user=self.student,
            question=self.q2,
            answer=self.b1,
            quiz_attempt=self.attempt,
        )
        Choice.objects.create(
            user=self.student,
            question=self.q2,
            answer=self.b2,
            quiz_attempt=self.attempt,
        )

        score = QuizAttemptService.calculate_score_for_attempt(self.attempt)
        self.assertEqual(score, 2)
        self.attempt.refresh_from_db()
        self.assertTrue(self.attempt.is_completed)

    def test_submit_test_attempt_success(self):
        payload = [
            {"question_id": self.q1.id, "chosen_answer_ids": [self.a1.id]},
            {"question_id": self.q2.id, "chosen_answer_ids": [self.b1.id, self.b2.id]},
        ]
        score = QuizAttemptService.submit_test_attempt(self.attempt, payload)
        self.assertEqual(score, 2)
        self.attempt.refresh_from_db()
        self.assertTrue(self.attempt.is_completed)
        self.assertEqual(self.attempt.score, 2)

    def test_submit_test_attempt_invalid_question(self):
        payload = [{"question_id": 99999, "chosen_answer_ids": [1]}]
        with self.assertRaises(serializers.ValidationError):
            QuizAttemptService.submit_test_attempt(self.attempt, payload)

    def test_submit_test_attempt_invalid_answer(self):
        payload = [{"question_id": self.q1.id, "chosen_answer_ids": [99999]}]
        with self.assertRaises(serializers.ValidationError):
            QuizAttemptService.submit_test_attempt(self.attempt, payload)

    def test_submit_test_attempt_multiple_for_single_choice(self):
        payload = [
            {"question_id": self.q1.id, "chosen_answer_ids": [self.a1.id, self.a2.id]}
        ]
        with self.assertRaises(serializers.ValidationError):
            QuizAttemptService.submit_test_attempt(self.attempt, payload)
