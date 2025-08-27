from rest_framework.exceptions import ValidationError
import re

def validate_video_url(value):
    """
    Валидатор для проверки корректности URL видео.
    Поддерживает YouTube и общие форматы URL.
    """
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&]+)'
    )
    if re.match(youtube_regex, value):
        return value
    if value.startswith(('http://', 'https://')) and '.' in value.split('//')[1]:
        return value
    raise ValidationError("Некорректный URL видео. Поддерживаются ссылки на YouTube или прямые ссылки.")

def validate_video_file_extension(value):
    """
    Валидатор для проверки расширения видеофайла.
    Поддерживает стандартные видеоформаты.
    """
    ext = str(value).split('.')[-1].lower()
    valid_extensions = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv']
    if ext not in valid_extensions:
        raise ValidationError(f"Неподдерживаемый формат видеофайла. Разрешенные форматы: {', '.join(valid_extensions)}")
    return value
