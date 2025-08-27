from rest_framework import serializers
from .models import Discipline
from Users.serializers import UserProfilePublicSerializer
from utils.mixins import ProfanityFilterMixin
from drf_spectacular.utils import extend_schema_field


class DisciplineSerializer(ProfanityFilterMixin, serializers.ModelSerializer):
    lesson_count = serializers.SerializerMethodField()
    # lessons = LessonSerializer(many=True, read_only=True)
    owner = UserProfilePublicSerializer(read_only=True)
    price_info = serializers.SerializerMethodField()
    user_has_access = serializers.SerializerMethodField()

    class Meta:
        model = Discipline
        fields = '__all__'
        profanity_fields = ['title', 'description']

    @extend_schema_field(serializers.IntegerField)
    def get_lesson_count(self, obj):
        return obj.lessons.count()

    @extend_schema_field(serializers.DictField)
    def get_price_info(self, obj):
        """
        Возвращает информацию о цене дисциплины.
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
        Проверяет, есть ли у текущего пользователя доступ к дисциплине.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        # Для студентов проверяем покупку
        if request.user.groups.filter(name='student').exists():
            from Payments.services import PaymentService
            return PaymentService.has_access_to_discipline(request.user, obj)

        # Для остальных ролей (учителя, админы, модераторы) - всегда true
        return True