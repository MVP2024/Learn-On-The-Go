from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from Disciplines.models import Discipline
from Lessons.models import Lesson, UserLessonProgress
from Lessons.serializers import LessonSerializer
from Payments.models import PriceConfiguration

User = get_user_model()


class LessonSerializersTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.teacher = User.objects.create_user(email="ser_teacher@a.aa", password="pw")
        self.student = User.objects.create_user(email="ser_student@a.aa", password="pw")
        Group.objects.get_or_create(name="student")
        self.student.groups.add(Group.objects.get(name="student"))
        self.disc = Discipline.objects.create(
            title="SerDisc", description="d", owner=self.teacher, slug="ser_disc"
        )
        self.lesson = Lesson.objects.create(
            title="SerLesson",
            discipline=self.disc,
            owner=self.teacher,
            lesson_order=1,
            video_url="https://example.com/video",
        )

    def test_user_progress_field_none_when_not_exists(self):
        req = self.factory.get("/api/lessons/")
        req.user = self.student
        ser = LessonSerializer(self.lesson, context={"request": req})
        data = ser.data
        self.assertIn("user_progress", data)
        self.assertIsNone(data["user_progress"])

    def test_user_progress_present_when_exists(self):
        progress = UserLessonProgress.objects.create(
            user=self.student,
            lesson=self.lesson,
            is_completed=False,
            watched_duration=10,
        )
        req = self.factory.get("/api/lessons/")
        req.user = self.student
        ser = LessonSerializer(self.lesson, context={"request": req})
        data = ser.data
        self.assertIsNotNone(data.get("user_progress"))
        up = data["user_progress"]
        # сериализатор прогресса должен включать watched_duration
        self.assertEqual(up.get("watched_duration"), progress.watched_duration)

    def test_get_price_info_returns_defaults_and_real(self):
        # без конфигурации цены -> возвращаются значения по умолчанию
        req = self.factory.get("/api/lessons/")
        req.user = self.student
        ser = LessonSerializer(self.lesson, context={"request": req})
        data = ser.data
        self.assertIn("price_info", data)
        self.assertIn("price", data["price_info"])

        # создаём PriceConfiguration для урока и проверяем, что возвращается текущая цена
        pc = PriceConfiguration.objects.create(
            lesson=self.lesson, price=100, is_free=False
        )
        ser2 = LessonSerializer(self.lesson, context={"request": req})
        data2 = ser2.data
        self.assertEqual(data2["price_info"]["price"], str(pc.price))

    def test_user_has_access_student_and_teacher(self):
        # по умолчанию студент не имеет доступа -> False
        req = self.factory.get("/api/lessons/")
        req.user = self.student
        with patch(
            "Payments.services.PaymentService.has_access_to_lesson", return_value=False
        ):
            ser = LessonSerializer(self.lesson, context={"request": req})
            self.assertFalse(ser.get_user_has_access(self.lesson))

        # подмена PaymentService на True -> студент получает доступ
        with patch(
            "Payments.services.PaymentService.has_access_to_lesson", return_value=True
        ):
            ser2 = LessonSerializer(self.lesson, context={"request": req})
            self.assertTrue(ser2.get_user_has_access(self.lesson))

        # преподаватели всегда имеют доступ
        req.user = self.teacher
        ser3 = LessonSerializer(self.lesson, context={"request": req})
        self.assertTrue(ser3.get_user_has_access(self.lesson))

    def test_validate_requires_either_video_url_or_video_file_but_not_both(self):
        from rest_framework.exceptions import ValidationError

        # оба поля заданы -> неверно
        data = {
            "title": "X",
            "discipline": self.disc.slug,
            "video_url": "https://a.example.com/video",
            "video_file": "file.mp4",
        }
        ser = LessonSerializer(data=data)
        with self.assertRaises(ValidationError):
            ser.is_valid(raise_exception=True)

        # ни одно из полей не задано -> неверно
        data2 = {"title": "X", "discipline": self.disc.slug}
        ser2 = LessonSerializer(data=data2)
        with self.assertRaises(ValidationError):
            ser2.is_valid(raise_exception=True)

        # только video_url -> валидно (используем корректный URL с доменом)
        data3 = {
            "title": "X",
            "discipline": self.disc.slug,
            "video_url": "https://ok.example.com/video",
        }
        ser3 = LessonSerializer(data=data3)
        self.assertTrue(ser3.is_valid())

        # только video_file (симулируем загрузку файла через SimpleUploadedFile) -> валидно
        uploaded = SimpleUploadedFile(
            "video.mp4", b"fakevideocontent", content_type="video/mp4"
        )
        data4 = {"title": "X", "discipline": self.disc.slug, "video_file": uploaded}
        ser4 = LessonSerializer(data=data4)
        self.assertTrue(ser4.is_valid())
