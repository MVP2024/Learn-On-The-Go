from rest_framework.exceptions import ValidationError

# Список запрещенных слов. Можно дополнить.
# Для реального проекта используйте более полный и гибкий список/библиотеку.
FORBIDDEN_WORDS = [
    "дурак", "идиот", "отстой", "чушь", "фигня", "дерьмо", "блин",
    "падла", "сука", "мудак", "гандон", "лох", "тупой", "дебил",
    "креведко", "медвед", "всу", "слава украине", "чурка", "хач",
    "fuck", "shit", "asshole", "bitch", "cunt", "damn", "hell", "piss",
    "suck", "whore", "bastard", "crap", "idiot", "moron", "retard",
    # Добавьте другие слова, если необходимо
]

def validate_profanity(value):
    """
    Валидатор, проверяющий текст на наличие запрещенных слов.
    Нечувствителен к регистру.
    """
    if not isinstance(value, str):
        return value # Пропускаем нестроковые значения, если они не должны валидироваться

    normalized_value = value.lower()
    for word in FORBIDDEN_WORDS:
        if word in normalized_value:
            raise ValidationError(f"Текст содержит запрещенное слово: '{word}'.")
    return value
