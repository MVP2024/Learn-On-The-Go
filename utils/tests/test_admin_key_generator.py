from django.test import TestCase

from utils.admin_key_generator import generate_key_and_message


class AdminKeyGeneratorTests(TestCase):
    """Тесты для генерации админ-ключа и формирования сообщения."""

    def test_generate_key_and_message_returns_tuple(self):
        class DummyUser:
            def __init__(self, email, first_name=None, last_name=None):
                self.email = email
                self.first_name = first_name
                self.last_name = last_name

            @property
            def full_name(self):
                fn = (self.first_name or "") + (
                    " " + (self.last_name or "") if self.last_name else ""
                )
                return fn.strip() or self.email

        u = DummyUser(email="u@example.com", first_name="Иван", last_name="Петров")
        key, msg = generate_key_and_message(u)
        # ключ — строка, сообщение содержит ключ и имя
        self.assertIsInstance(key, str)
        self.assertTrue(len(key) > 10)
        self.assertIn(key, msg)
        self.assertIn("Иван", msg)
