import re

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from Disciplines.models import Discipline

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
    "ъ": "'",
    "ы": "y",
    "ь": ",",
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
    if not _contains_cyrillic(text):
        return text
    out = []
    for ch in text:
        out.append(_CYR_TO_LAT.get(ch, ch))
    result = "".join(out)
    result = re.sub(r"[^a-z0-9\s\-_]", "", result)
    result = re.sub(r"\s+", "-", result).strip("-")
    return result or "discipline"


class Command(BaseCommand):
    help = """Генерирует уникальные slug для всех дисциплин, у которых slug пустой.

    Команда idempotent — можно запускать несколько раз. При большом количестве записей
    используйте опцию --batch для контроля размера пачки. Добавлена опция --force для перезаписи существующих slug'ов.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch",
            type=int,
            default=100,
            help="Размер пачки при обработке (по умолчанию 100)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Не сохранять изменения, просто вывести, какие slugs будут сгенерированы",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Перезаписать slug даже если он уже заполнен",
        )

    def handle(self, *args, **options):
        batch = options.get("batch")
        dry_run = options.get("dry_run")
        force = options.get("force")

        if force:
            qs = Discipline.objects.all().order_by("id")
        else:
            qs = Discipline.objects.filter(slug__isnull=True).order_by("id")

        total = qs.count()
        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "Нет дисциплин для обработки (slug пустые или нет запросов)."
                )
            )
            return

        self.stdout.write(
            f"Найдено дисциплин для обработки: {total}. Обработка пачками по {batch}..."
        )

        processed = 0
        # выполняем итерацию
        start = 0
        while True:
            objs = list(qs[start : start + batch])
            if not objs:
                break

            with transaction.atomic():
                for obj in objs:
                    # Если не force и slug существует — пропускаем
                    if obj.slug and not force:
                        self.stdout.write(
                            f"skip (exists): id={obj.pk}, slug={obj.slug}"
                        )
                        processed += 1
                        continue

                    # Если title на кириллице — транслитерируем, иначе используем title как есть (lowercased)
                    if obj.title:
                        base = (
                            _transliterate(obj.title)
                            if _contains_cyrillic(obj.title)
                            else obj.title.lower()
                        )
                    else:
                        base = str(obj.pk)

                    candidate = f"{base}_{obj.pk}"
                    candidate = slugify(candidate)

                    unique_slug = candidate
                    counter = 0
                    # обеспечиваем уникальность
                    while (
                        Discipline.objects.filter(slug=unique_slug)
                        .exclude(pk=obj.pk)
                        .exists()
                    ):
                        counter += 1
                        unique_slug = f"{candidate}-{counter}"

                    if dry_run:
                        self.stdout.write(
                            f"[dry-run] {obj.pk}: would set slug='{unique_slug}' (title='{obj.title}')"
                        )
                    else:
                        Discipline.objects.filter(pk=obj.pk).update(slug=unique_slug)
                        self.stdout.write(
                            f"{obj.pk}: set slug='{unique_slug}' (title='{obj.title}')"
                        )

                    processed += 1

            start += batch

        self.stdout.write(
            self.style.SUCCESS(f"Готово. Обработано: {processed} дисциплин.")
        )
