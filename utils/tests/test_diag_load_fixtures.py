import json
import tempfile
from pathlib import Path

from django.test import TestCase

from utils.diag_load_fixtures import read_fixture, try_deserialize_one


class DiagLoadFixturesTests(TestCase):
    """Тесты для утилиты utils/diag_load_fixtures."""

    def test_read_fixture_valid_json(self):
        data = [{"model": "Users.user", "pk": 1, "fields": {}}]
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(data, fh, ensure_ascii=False)
            path = Path(fh.name)
        loaded = read_fixture(path)
        self.assertIsInstance(loaded, list)
        path.unlink()

    def test_try_deserialize_one_malformed(self):
        # Пытаемся десериализовать объект с неизвестной моделью — ожидаем False
        bogus = {"model": "No.such.model", "pk": 1, "fields": {}}
        ok, info = try_deserialize_one(bogus)
        self.assertFalse(ok)
        self.assertIn(info[0], ("deserialization", "save"))
