from rest_framework import serializers

from Disciplines.models import Section, Discipline
from .models import Lesson, UserLessonProgress
from .validators import validate_video_url, validate_video_file_extension
from utils.mixins import ProfanityFilterMixin
from drf_spectacular.utils import extend_schema_field


class UserLessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLessonProgress
        fields = '__all__'
        read_only_fields = ('user', 'lesson', 'is_completed', 'watched_duration', 'last_watched_at')


class LessonSerializer(ProfanityFilterMixin, serializers.ModelSerializer):
    video_url = serializers.URLField(
        required=False,
        allow_blank=True,
        validators=[validate_video_url],
        help_text="URL видео урока (например, ссылка на RuTube)."
    )
    video_file = serializers.FileField(
        required=False,
        allow_null=True,
        validators=[validate_video_file_extension],
        help_text="Файл видео урока (допустимые форматы: .mp4, .avi, .mov, mkv, webm, flv)."
    )
    # Добавляем поле для отображения прогресса пользователя
    user_progress = serializers.SerializerMethodField()
    discipline = serializers.SlugRelatedField(
        slug_field="title",
        queryset=Discipline.objects.all(),
        help_text="Название дисциплины, к которой относится урок.",
    )
    section = serializers.SlugRelatedField(
        slug_field="title",
        queryset=Section.objects.all(),
        required=False,
        allow_null=True,
        help_text="Название раздела дисциплины, к которому относится урок (необязательно).",
    )
    price_info = serializers.SerializerMethodField()
    user_has_access = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = "__all__"
        profanity_fields = ["title", "description"]

    @extend_schema_field(UserLessonProgressSerializer)
    def get_user_progress(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            try:
                progress = UserLessonProgress.objects.get(user=request.user, lesson=obj)
                return UserLessonProgressSerializer(progress).data
            except UserLessonProgress.DoesNotExist:
                return None
        return None

    @extend_schema_field(serializers.DictField)
    def get_price_info(self, obj):
        """
        Возвращает информацию о цене урока.
        """
        try:
            price_config = obj.price_config
            return {
                'price': str(price_config.price),
                'current_price': str(price_config.get_current_price()),
                'is_free': price_config.is_free,
                'discount_price': str(price_config.discount_price) if price_config.discount_price else None,
                'discount_end_date': price_config.discount_end_date,
                'has_discount': bool(price_config.discount_price and price_config.discount_end_date)
            }
        except Exception:
            return {
                'price': None,
                'current_price': None,
                'is_free': False,
                'discount_price': None,
                'discount_end_date': None,
                'has_discount': False
            }

    @extend_schema_field(serializers.BooleanField)
    def get_user_has_access(self, obj):
        """
        Проверяет, есть ли у текущего пользователя доступ к уроку.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        # Для студентов проверяем покупку
        if request.user.groups.filter(name='student').exists():
            from Payments.services import PaymentService
            return PaymentService.has_access_to_lesson(request.user, obj)

        # Для остальных ролей (учителя, админы, модераторы) - всегда true
        return True

    def validate(self, data):
        # Проверяем, что заполнен либо video_url, либо video_file, но не оба
        if data.get("video_url") and data.get("video_file"):
            raise serializers.ValidationError(
                "Нельзя загружать видео по URL и файлом одновременно. Выберите что-то одно."
            )
        if not data.get("video_url") and not data.get("video_file"):
            raise serializers.ValidationError(
                "Необходимо предоставить либо URL видео, либо видеофайл."
            )
        return data
