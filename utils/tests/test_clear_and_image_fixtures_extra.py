import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from utils.clear_and_load_fixtures import load_fixtures
from utils.image_validators import validate_image_file


class LoadFixturesPermissionBypassTests(TestCase):
    def test_load_fixtures_handles_permission_deserialization_error_and_retries_without_perms(
        self,
    ):
        # Создаём временный фикстурный файл с одной записью auth.permission и одной другой
        data = [
            {"model": "auth.permission", "pk": 1, "fields": {}},
            {"model": "Users.user", "pk": 1, "fields": {}},
        ]
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(data, fh, ensure_ascii=False)
            path = Path(fh.name)
        try:
            # Первый вызов call_command будет бросать ошибку, содержащую 'Permission has no content_type'
            # Второй вызов должен пройти успешно
            def side_effect_loaddata(*args, **kwargs):
                if len(args) >= 2:
                    p = str(args[1])
                else:
                    p = str(kwargs.get("path") or "")
                if p.endswith(".noperms.json"):
                    return None
                raise Exception("Permission has no content_type for some reason")

            with patch(
                "utils.clear_and_load_fixtures.call_command",
                side_effect=side_effect_loaddata,
            ) as mock_call:
                # Запускаем функцию — она должна обработать исключение, создать .noperms.json и вызвать loaddata снова
                load_fixtures(path, verbosity=0)
                # Должны быть вызовы loaddata как минимум 2 раза (оригинал и временный .noperms)
                self.assertGreaterEqual(mock_call.call_count, 2)
                # Проверяем, что один из вызовов был с файлом .noperms.json
                found_tmp = False
                for call in mock_call.call_args_list:
                    args, kwargs = call
                    # args can be ('loaddata', path)
                    if len(args) >= 2 and str(args[1]).endswith(".noperms.json"):
                        found_tmp = True
                        break
                self.assertTrue(
                    found_tmp, "Expected a call with .noperms.json temporary fixture"
                )
        finally:
            try:
                path.unlink()
            except Exception:
                pass
            try:
                tmp = path.with_suffix(".noperms.json")
                tmp.unlink()
            except Exception:
                pass


class ImageValidatorsExtraTests(TestCase):
    def test_unidentified_image_raises_validation_error(self):
        fake = SimpleUploadedFile(
            "bad.img", b"not-an-image", content_type="image/octet-stream"
        )
        with patch(
            "utils.image_validators.Image.open", side_effect=UnidentifiedImageError()
        ):
            with self.assertRaises(ValidationError):
                validate_image_file(fake)

    def test_unsupported_format_raises_validation_error(self):
        fake = SimpleUploadedFile("bmp_like.img", b"bmp-data", content_type="image/bmp")

        class FI:
            format = "BMP"

        with patch("utils.image_validators.Image.open", return_value=FI()):
            with patch(
                "utils.image_validators.get_image_dimensions", return_value=(100, 100)
            ):
                with self.assertRaises(ValidationError):
                    validate_image_file(fake)

    def test_none_dimensions_raises_validation_error(self):
        fake = SimpleUploadedFile("png.img", b"png-data", content_type="image/png")

        class FI2:
            format = "PNG"

        with patch("utils.image_validators.Image.open", return_value=FI2()):
            with patch(
                "utils.image_validators.get_image_dimensions", return_value=(None, None)
            ):
                with self.assertRaises(ValidationError):
                    validate_image_file(fake)
