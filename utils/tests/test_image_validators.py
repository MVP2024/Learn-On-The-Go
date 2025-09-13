from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from utils.image_validators import validate_image_file


class ImageValidatorsTests(TestCase):
    """Тестируем validate_image_file — проверяем поведение на корректных и некорректных файлах."""

    @staticmethod
    def test_validate_accepts_small_png():
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x02\x00\x01\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82"
        small_png = SimpleUploadedFile("small.png", png_bytes, content_type="image/png")
        validate_image_file(small_png)

    def test_validate_rejects_large_file(self):
        big = SimpleUploadedFile(
            "big.jpg", b"0" * (11 * 1024 * 1024), content_type="image/jpeg"
        )
        with self.assertRaises(ValidationError):
            validate_image_file(big)

    def test_validate_rejects_invalid_image(self):
        fake = SimpleUploadedFile(
            "text.txt", b"not-an-image", content_type="text/plain"
        )
        with self.assertRaises(ValidationError):
            validate_image_file(fake)
