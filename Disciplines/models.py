import re

from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import Index
from django.db.models.functions import Lower
from django.utils.text import slugify

from Users.models import User
from utils.image_validators import validate_image_file

# Простая таблица транслитерации кириллицы -> латиница (подходит для русских названий)
_CYR_TO_LAT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "'",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def _contains_cyrillic(text: str) -> bool:
    return bool(re.search("[\u0400-\u04ff]", text))


def _transliterate(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    # Быстрая проверка: если нет кириллицы — возвращаем оригинал (lowercase)
    if not _contains_cyrillic(text):
        # нормализуем: оставляем только ascii letters/digits/space/-/_
        cleaned = re.sub(r"[^a-z0-9\s\-_]", "", text)
        return re.sub(r"\s+", "-", cleaned).strip("-") or "discipline"
    out = []
    for ch in text:
        out.append(_CYR_TO_LAT.get(ch, ch))
    result = "".join(out)
    # Оставляем только латинские символы, цифры, дефисы и нижние подчёркивания
    result = re.sub(r"[^a-z0-9\s\-_]", "", result)
    result = re.sub(r"\s+", "-", result).strip("-")
    return result or "discipline"


class Discipline(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название")
    slug = models.SlugField(
        max_length=255, unique=True, null=True, blank=True, verbose_name="SLUG"
    )
    preview = models.ImageField(
        validators=[validate_image_file],
        upload_to="previews/",
        null=True,
        blank=True,
        verbose_name="Превью",
    )
    description = models.TextField(verbose_name="Описание")
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Владелец",
        null=True,  # Будет null, если создано модератором
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок отображения",
        help_text="Порядок дисциплины в общем каталоге (1, 2, 3...)",
        db_index=True,
    )

    def __str__(self):
        return self.title

    def _generate_candidate(self, pk: int) -> str:
        """
        Формирует базовый candidate для slug.
        - Если title содержит кириллицу — транслитерируем.
        - Если title уже на латинице — используем его (lowercased).
        После этого добавляем _{pk} чтобы гарантировать детерминированную уникальность.
        """
        base = _transliterate(self.title) if self.title else str(pk)
        candidate = f"{base}_{pk}" if base else str(pk)
        # Нормализуем через slugify чтобы убрать лишние символы
        return slugify(candidate)

    def save(self, *args, **kwargs):
        """
        Автоматически генерируем человеко-читабельный slug в формате <translit_or_title>_<id>
        если slug не указан явно.
        Реализация безопасна для новых объектов (сначала сохраняем, чтобы получить id),
        и для существующих — если slug пустой, сразу генерируем и обновляем запись.
        """
        # Если slug уже заполнен — сохраняем без изменений
        if self.slug:
            super().save(*args, **kwargs)
            return
        is_new = self.pk is None
        if is_new:
            # Сохраняем, чтобы получить pk
            super().save(*args, **kwargs)
            # Теперь pk доступен — генерируем slug
            candidate = self._generate_candidate(self.pk)
            unique_slug = candidate
            counter = 0
            while (
                Discipline.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists()
            ):
                counter += 1
                unique_slug = f"{candidate}-{counter}"
            # Обновляем только поле slug (чтобы не запустить рекурсивный save)
            Discipline.objects.filter(pk=self.pk).update(slug=unique_slug)
            # Обновляем инстанс в памяти чтобы сериализатор видел slug
            self.slug = unique_slug
        else:
            # Объект уже существует. Если slug пустой — генерируем на основе pk
            candidate = self._generate_candidate(self.pk)
            unique_slug = candidate
            counter = 0
            while (
                Discipline.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists()
            ):
                counter += 1
                unique_slug = f"{candidate}-{counter}"
            self.slug = unique_slug
            super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"
        ordering = ["order", "title"]
        indexes = [
            Index(Lower("title"), name="discipline_title_lower_idx"),
            GinIndex(
                fields=["title"],
                name="discipline_title_trgm_gin",
                opclasses=["gin_trgm_ops"],
            ),
        ]


class Section(models.Model):
    """
    Раздел дисциплины (например: "Глава 1", "Модуль 2")
    """

    title = models.CharField(
        max_length=200,
        verbose_name="Название раздела",
        help_text="Например: 'Глава 1. Основы алгебры'",
    )
    section_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Номер раздела",
        help_text="Порядок раздела в дисциплине (1, 2, 3...)",
        db_index=True,
    )
    discipline = models.ForeignKey(
        Discipline,
        on_delete=models.CASCADE,
        related_name="sections",
        verbose_name="Дисциплина",
    )

    def __str__(self):
        return f"{self.title} ({self.discipline.title if self.discipline else '—'})"

    class Meta:
        verbose_name = "Раздел дисциплины"
        verbose_name_plural = "Разделы дисциплин"
        ordering = ["section_order"]
        unique_together = (("discipline", "section_order"),)
