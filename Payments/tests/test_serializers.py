from django.test import TestCase

from Payments.serializers import CreatePaymentSerializer


class PaymentsSerializersTests(TestCase):
    """Тесты валидации CreatePaymentSerializer."""

    def test_validate_requires_discipline_id_for_discipline(self):
        data = {"payment_type": "discipline"}
        ser = CreatePaymentSerializer(data=data)
        self.assertFalse(ser.is_valid())

    def test_validate_for_lesson_requires_lesson_id(self):
        data = {"payment_type": "lesson"}
        ser = CreatePaymentSerializer(data=data)
        self.assertFalse(ser.is_valid())

    def test_validate_rejects_both_ids(self):
        data = {"payment_type": "lesson", "lesson_id": 1, "discipline_id": 2}
        ser = CreatePaymentSerializer(data=data)
        self.assertFalse(ser.is_valid())

    def test_validate_accepts_correct_discipline_payload(self):
        data = {"payment_type": "discipline", "discipline_id": 1}
        ser = CreatePaymentSerializer(data=data)
        # сериализатор проверяет присутствие дисциплины
        self.assertTrue(ser.is_valid())

    def test_validate_accepts_correct_lesson_payload(self):
        data = {"payment_type": "lesson", "lesson_id": 1}
        ser = CreatePaymentSerializer(data=data)
        self.assertTrue(ser.is_valid())
