from django.db import models
from Users.models import User
from utils.image_validators import validate_image_file


class Discipline(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название")
    preview = models.ImageField(
        validators=[validate_image_file],
        upload_to='previews/',
        null=True,
        blank=True,
        verbose_name="Превью"
    )
    description = models.TextField(verbose_name="Описание")
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Владелец",
        null=True,  # Будет null, если создано модератором
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок отображения",
        help_text="Порядок дисциплины в общем каталоге (1, 2, 3...)",
        db_index=True
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"
        ordering = ["order", "title"]


class Section(models.Model):
    """
    Разделы внутри дисциплины.
    Например: "Алгебра" -> "Раздел 1. Основы", "Раздел 2. Уравнения"
    """
    title = models.CharField(
        max_length=200,
        verbose_name="Название раздела",
        help_text="Например: 'Глава 1. Основы алгебры', 'Модуль 2. Уравнения'"
    )
    discipline = models.ForeignKey(
        Discipline,
        on_delete=models.CASCADE,
        related_name='sections',
        verbose_name="Дисциплина"
    )
    section_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Номер раздела",
        help_text="Порядок раздела в дисциплине (1, 2, 3...)",
        db_index=True
    )

    class Meta:
        verbose_name = "Раздел дисциплины"
        verbose_name_plural = "Разделы дисциплин"
        ordering = ['section_order']
        unique_together = ('discipline', 'section_order')  # Уникальный номер раздела в дисциплине

    def __str__(self):
        return f"Раздел {self.section_order}: {self.title} ({self.discipline.title})"
