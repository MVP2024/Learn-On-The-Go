from django.core.files.images import get_image_dimensions
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


def validate_image_file(image):
    """
    Валидатор для проверки формата и размера загружаемого изображения.
    Поддерживает JPEG/PNG/GIF и размер до 10 МБ.
    """
    allowed_formats = {"JPEG", "PNG", "GIF"}
    max_size = 10 * 1024 * 1024  # 10 MB

    # Проверка размера
    if image.size > max_size:
        raise ValidationError(
            f"Размер файла не должен превышать {max_size // (1024 * 1024)} МБ."
        )

    # Проверяем реальный формат картинки через Pillow (защита от подмены расширения)
    try:
        # Убеждаемся, что чтение начнётся с начала
        image.file.seek(0)
        img = Image.open(image.file)
        img_format = getattr(img, "format", None)
        if img_format not in allowed_formats:
            raise ValidationError(
                f"Неподдерживаемый формат файла. Разрешены: {', '.join(sorted(allowed_formats))}."
            )
        # Дополнительная проверка размеров (тоже безопаснее)
        w, h = get_image_dimensions(image)
        if w is None or h is None:
            raise ValidationError(
                "Не удалось определить размеры изображения. Возможно, файл поврежден."
            )
    except UnidentifiedImageError:
        raise ValidationError("Некорректный файл изображения.")
    except ValidationError:
        raise
    except Exception:
        raise ValidationError("Некорректный файл изображения.")
    finally:
        try:
            image.file.seek(0)
        except Exception:
            pass
