from rest_framework import serializers
from utils.profanity_filter import validate_profanity

class ProfanityFilterMixin(serializers.Serializer):
    """
    Миксин для сериализаторов, который применяет валидацию на наличие
    запрещенных слов ко всем строковым полям, указанным в `Meta.profanity_fields`.
    """
    class Meta:
        # Добавляем пустой Meta класс по умолчанию, чтобы избежать предупреждения IDE
        # Сериализаторы, использующие этот миксин, будут переопределять profanity_fields
        pass

    def validate(self, attrs):
        # Вызываем родительский метод validate для выполнения стандартных проверок
        attrs = super().validate(attrs)

        # Проверяем, есть ли список полей для валидации на мат в Meta классе
        profanity_fields = getattr(self.Meta, 'profanity_fields', [])

        for field_name in profanity_fields:
            if field_name in attrs and isinstance(attrs[field_name], str):
                validate_profanity(attrs[field_name])
        return attrs