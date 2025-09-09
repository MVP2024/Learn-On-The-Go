from django.contrib.auth import get_user_model
from django.test import TestCase

from Disciplines.models import Discipline
from Exercises.models import Answer, Question, QuizAttempt, Test
from Exercises.serializers import AnswerSerializer, SubmitTestSerializer
from Lessons.models import Lesson

User = get_user_model()


class SerializersTests(TestCase):
    """Тесты сериализаторов (AnswerSerializer, SubmitTestSerializer)."""

    def setUp(self):
        self.teacher = User.objects.create_user(email="t3@example.com", password="pw")
        self.student = User.objects.create_user(email="s3@example.com", password="pw")
        self.discipline = Discipline.objects.create(
            title="D3", description="d", owner=self.teacher
        )
        self.lesson = Lesson.objects.create(
            title="L3", discipline=self.discipline, owner=self.teacher, lesson_order=1
        )
        self.test = Test.objects.create(
            title="T3",
            discipline=self.discipline,
            lesson=self.lesson,
            owner=self.teacher,
        )
        self.q = Question.objects.create(
            test=self.test, text="X?", question_order=1, is_multiple=False
        )
        self.correct = Answer.objects.create(
            question=self.q, text="yes", is_correct=True
        )
        self.wrong = Answer.objects.create(question=self.q, text="no", is_correct=False)

    def test_answer_serializer_hides_is_correct_for_unauthenticated(self):
        ser = AnswerSerializer(self.correct, context={})
        data = ser.data
        self.assertNotIn("is_correct", data)

    def test_answer_serializer_shows_is_correct_for_teacher(self):
        # создаём имитацию request с user
        request_obj = type("Req", (), {"user": self.teacher})()
        ser = AnswerSerializer(self.correct, context={"request": request_obj})
        data = ser.data
        self.assertIn("is_correct", data)

    def test_answer_serializer_shows_for_student_after_completed_attempt(self):
        QuizAttempt.objects.create(user=self.student, quiz=self.test, is_completed=True)
        request_obj = type("Req", (), {"user": self.student})()
        ser = AnswerSerializer(self.correct, context={"request": request_obj})
        data = ser.data
        self.assertIn("is_correct", data)
        self.assertTrue(data["is_correct"])

    def test_submit_serializer_validation(self):
        # пустые ответы
        ser = SubmitTestSerializer(data={"answers": []})
        self.assertFalse(ser.is_valid())
        # неправильная форма
        ser = SubmitTestSerializer(data={"answers": ["not-a-dict"]})
        self.assertFalse(ser.is_valid())
        # правильная форма
        ser = SubmitTestSerializer(
            data={
                "answers": [
                    {"question_id": self.q.id, "chosen_answer_ids": [self.correct.id]}
                ]
            }
        )
        self.assertTrue(ser.is_valid())
