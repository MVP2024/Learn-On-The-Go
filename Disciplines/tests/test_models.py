from django.test import TestCase
from django.utils.text import slugify

from Disciplines.models import Discipline, _contains_cyrillic, _transliterate


class TransliterationAndSlugTests(TestCase):
    """Проверяем транслитерацию, определение кириллицы и генерацию slug в модели Discipline."""

    def test_contains_cyrillic_and_transliterate(self):
        cases = [
            ("Математика", True),
            ("matematika", False),
            ("12345", False),
            ("Русский текст", True),
            ("English Text", False),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(_contains_cyrillic(text), expected)

        # Простейшая проверка транслитерации (не полный набор)
        t = _transliterate("Математика")
        self.assertIsInstance(t, str)
        # получаем "похожее" представление: в нём не должно быть кириллицы
        self.assertFalse(_contains_cyrillic(t))

    def test_slug_generated_on_save_for_new_object(self):
        d = Discipline.objects.create(
            title="Моя дисциплина для теста", description="desc"
        )
        # После создания slug должен быть заполнен и содержать pk
        self.assertIsNotNone(d.slug)
        self.assertIn(str(d.pk), d.slug)
        # slug корректно нормализован
        self.assertEqual(d.slug, slugify(d.slug))

    def test_slug_uniqueness_for_same_titles(self):
        title = "Одинаковое название"
        a = Discipline.objects.create(title=title, description="a")
        b = Discipline.objects.create(title=title, description="b")
        self.assertNotEqual(a.slug, b.slug)
        # Оба slug'а не пустые и содержат pk
        self.assertIn(str(a.pk), a.slug)
        self.assertIn(str(b.pk), b.slug)
