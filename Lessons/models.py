from django.db import models

from Disciplines.models import Discipline, Section
from Users.models import User
from utils.image_validators import validate_image_file


class Lesson(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название урока")
    description = models.TextField(
        max_length=1000, verbose_name="Описание урока", blank=True, null=True
    )
    preview = models.ImageField(
        validators=[validate_image_file],
        upload_to="lesson_previews/",
        null=True,
        blank=True,
        verbose_name="Превью урока",
    )
    video_url = models.URLField(blank=True, null=True, verbose_name="URL видео")
    video_file = models.FileField(
        upload_to="lesson_videos/", blank=True, null=True, verbose_name="Видео файл"
    )
    discipline = models.ForeignKey(
        Discipline,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name="Предмет",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        related_name="lessons",
        verbose_name="Раздел дисциплины",
        null=True,
        blank=True,
        help_text="К какому разделу дисциплины относится урок (например: 'Глава 1. Введение', 'Тема: Дроби')."
        " Если не указан - урок будет в общем списке дисциплины."
        " Вы можете создать разделы в разделе 'Предметы'",
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name="Владелец урока",
        null=True,  # Будет null, если создано модератором
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    lesson_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Номер урока",
        help_text="Порядковый номер урока в разделе или дисциплине (1, 2, 3...)",
        db_index=True,
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"
        ordering = [
            "discipline",
            "section",
            "lesson_order",
        ]  # Сортировка по дисциплине, разделу, номеру урока


class UserLessonProgress(models.Model):
    """
    Тут записываем прогресс студента по урокам.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="lesson_progresses",
        verbose_name="Пользователь",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="user_progresses",
        verbose_name="Урок",
    )
    is_completed = models.BooleanField(default=False, verbose_name="Урок пройден")
    current_time = models.FloatField(
        default=0.0, verbose_name="Текущее время воспроизведения (сек)"
    )
    watched_duration = models.IntegerField(default=0, verbose_name="Просмотрено секунд")
    last_watched_at = models.DateTimeField(
        auto_now=True, verbose_name="Последний просмотр"
    )

    class Meta:
        verbose_name = "Прогресс урока пользователя"
        verbose_name_plural = "Прогресс уроков пользователей"
        unique_together = (
            "user",
            "lesson",
        )  # Один прогресс на одного пользователя на один урок

    def __str__(self):
        """
        Возвращает строковое представление прогресса урока.
        """
        return f"{self.user.email} - {self.lesson.title}: {'Пройден' if self.is_completed else 'Не пройден'}"
