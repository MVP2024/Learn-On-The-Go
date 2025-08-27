from rest_framework.exceptions import ValidationError
from django.core.files.images import get_image_dimensions

def validate_image_file(image):
    """
    Валидатор для проверки формата и размера загружаемого изображения.
    Поддерживает JPEG/PNG и размер до 10 МБ.
    """
    # Проверка формата
    if not image.name.lower().endswith(('.jpg', '.jpeg', '.png')):
        raise ValidationError("Неподдерживаемый формат файла. Разрешены только JPEG и PNG.")

    # Проверка размера (10 МБ = 10 * 1024 * 1024 байт)
    max_size = 10 * 1024 * 1024
    if image.size > max_size:
        raise ValidationError(f"Размер файла не должен превышать {max_size / (1024 * 1024):.0f} МБ.")

    # Дополнительная проверка на действительность изображения
    try:
        w, h = get_image_dimensions(image)
        if w is None or h is None:
            raise ValidationError("Не удалось определить размеры изображения. Возможно, файл поврежден.")
    except Exception:
        raise ValidationError("Некорректный файл изображения.")
