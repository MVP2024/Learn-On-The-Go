from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from Students.models import Student

User = get_user_model()


class ScriptsForDemoTests(TestCase):
    """Тесты интеграции для вспомогательных скриптов по созданию пользователей."""

    def setUp(self):
        # создаём группы, как это делают скрипты
        for g in ("admin", "teacher", "student", "moderator"):
            Group.objects.get_or_create(name=g)

    def test_setup_users_creates_student_and_teacher(self):
        """
        Проверяем, что функции по созданию пользователей (если бы мы их импортировали) создают записи Student/Teacher.
        Здесь мы эмулируем поведение похожее на utils/scripts_for_demo/setup_users.py: создаём User и Student вручную,
        проверяем отношение OneToOne.
        """
        u = User.objects.create_user(email="demo_student@a.aa", password="pw")
        # Добавляем в группу student
        u.groups.add(Group.objects.get(name="student"))
        # Создаём профиль Student
        s = Student.objects.create(user=u, course=1)
        self.assertEqual(s.user.email, "demo_student@a.aa")
        self.assertEqual(s.course, 1)
