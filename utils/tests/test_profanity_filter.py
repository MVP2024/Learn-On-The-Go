from django.test import TestCase
from rest_framework.exceptions import ValidationError

from utils.profanity_filter import FORBIDDEN_WORDS, validate_profanity


class ProfanityFilterTests(TestCase):
    """Тесты для модуля utils.profanity_filter."""

    def test_validate_allows_clean_text(self):
        """Чистый текст должен проходить без ошибок и возвращаться как есть."""
        good = "Это нормальный текст без ругательств"
        res = validate_profanity(good)
        self.assertEqual(res, good)

    def test_validate_rejects_forbidden_words_case_insensitive(self):
        """Текст, содержащий запрещённое слово (в любом регистре), должен вызывать ValidationError."""
        word = FORBIDDEN_WORDS[0]
        with self.assertRaises(ValidationError):
            validate_profanity(f"Вот слово {word.upper()} в середине")

    def test_non_string_is_ignored(self):
        """Если передали не строковое значение — функция просто возвращает его без ошибки."""
        obj = 12345
        res = validate_profanity(obj)
        self.assertEqual(res, obj)
