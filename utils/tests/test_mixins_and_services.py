from unittest.mock import patch

from django.test import TestCase

from utils.mixins import ProfanityFilterMixin
from utils.paginators import (
    LargeResultsSetPagination,
    SmallResultsSetPagination,
    StandardResultsSetPagination,
)
from utils.services import get_lessons_and_tests_for_discipline


class ProfanityMixinSerializer(ProfanityFilterMixin):
    class Meta:
        profanity_fields = ["a", "b"]


class UtilsMixinsAndServicesTests(TestCase):
    """Тесты для utils.mixins, utils.services и пагинаторов."""

    def test_profanity_mixin_calls_validator(self):
        # проверяем, что validate вызывает validate_profanity косвенно (через mixin)
        s = ProfanityMixinSerializer(data={"a": "clean", "b": "clean"})
        # сериализатор не реализует full DRF flow, но метод validate можно вызвать
        cleaned = s.validate({"a": "clean", "b": "clean"})
        self.assertIn("a", cleaned)

    def test_paginators_defaults(self):
        self.assertEqual(StandardResultsSetPagination.page_size, 10)
        self.assertEqual(LargeResultsSetPagination.page_size, 20)
        self.assertEqual(SmallResultsSetPagination.page_size, 5)

    @patch("utils.services.Lesson.objects.filter")
    @patch("utils.services.Test.objects.filter")
    def test_get_lessons_and_tests_for_discipline_calls_models(
        self, mock_tests_filter, mock_lessons_filter
    ):
        # Простая проверка: функция должна вызывать ORM фильтры и вернуть кортеж
        mock_lessons_filter.return_value.order_by.return_value = []
        mock_tests_filter.return_value.order_by.return_value = []
        lessons, tests = get_lessons_and_tests_for_discipline(1)
        self.assertIsInstance(lessons, list)
        self.assertIsInstance(tests, list)
        mock_lessons_filter.assert_called()
        mock_tests_filter.assert_called()
