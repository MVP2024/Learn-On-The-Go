from django.contrib.auth import get_user_model
from django.test import TestCase

from Disciplines.models import Discipline
from Teachers.models import Teacher

User = get_user_model()


class TeacherModelTests(TestCase):
    """Тесты модели Teacher: строковое представление и связь с дисциплинами."""

    def setUp(self):
        # Создаём пользователя и дисциплины
        self.user = User.objects.create_user(email="t_model@a.aa", password="pw")
        self.teacher = Teacher.objects.create(user=self.user)
        self.disc1 = Discipline.objects.create(
            title="Disc One", description="d", owner=self.user, slug="disc-one"
        )
        self.disc2 = Discipline.objects.create(
            title="Disc Two", description="d", owner=self.user, slug="disc-two"
        )

    def test_str_contains_full_name_and_role(self):
        """__str__ должен содержать email/имя пользователя и слово 'Преподаватель'."""
        s = str(self.teacher)
        self.assertIn(self.user.email, s)
        self.assertIn("Преподаватель", s)

    def test_disciplines_m2m_relation(self):
        """Проверяем связь ManyToMany disciplines: добавляем дисциплины и читаем их."""
        # добавляем дисциплины
        self.teacher.disciplines.add(self.disc1, self.disc2)
        self.assertEqual(self.teacher.disciplines.count(), 2)
        titles = {d.title for d in self.teacher.disciplines.all()}
        self.assertIn("Disc One", titles)
        self.assertIn("Disc Two", titles)
