from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from Students.models import Student

User = get_user_model()


class StudentModelTests(TestCase):
    """Тесты поведения модели Student."""

    def setUp(self):
        # Создаём пользователя, к которому привяжем Student
        self.user = User.objects.create_user(email="stu@example.com", password="pw")

    def test_create_student_and_str(self):
        """Проверяем, что Student создаётся и __str__ содержит email/имя."""
        student = Student.objects.create(user=self.user, course=2)
        # __str__ возвращает "<full_name> - Студент"
        self.assertIn(str(self.user.email), str(student))
        self.assertIn("Студент", str(student))

    def test_one_to_one_constraint(self):
        """Попытка создать второго Student для того же User должна упасть (IntegrityError)."""
        Student.objects.create(user=self.user, course=1)
        with self.assertRaises(IntegrityError):
            # Второй create должен нарушить PK/OneToOne ограничение
            Student.objects.create(user=self.user, course=2)

    def test_course_choices_acceptance(self):
        """Поля course принимают значения из COURSE_CHOICES и None."""
        # None (по умолчанию) — допустимо
        s_none = Student.objects.create(
            user=User.objects.create_user(email="snone@example.com", password="pw")
        )
        self.assertIsNone(s_none.course)

        # Проверяем что все варианты из choices можно сохранить
        for val, _label in Student.COURSE_CHOICES:
            u = User.objects.create_user(email=f"stu{val}@example.com", password="pw")
            s = Student.objects.create(user=u, course=val)
            self.assertEqual(s.course, val)
