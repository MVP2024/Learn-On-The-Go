"""
Сериализаторы для системы платежей.
Здесь описаны все форматы данных для работы с платежами, ценами и покупками.
"""
from rest_framework import serializers
from .models import Payment, PurchasedContent, PriceConfiguration
from Disciplines.serializers import DisciplineSerializer
from Lessons.serializers import LessonSerializer
from drf_spectacular.utils import extend_schema_field

class PriceConfigurationSerializer(serializers.ModelSerializer):
    current_price = serializers.SerializerMethodField()

    class Meta:
        model = PriceConfiguration
        fields = [
            'id', 'discipline', 'lesson', 'price', 'is_free', 
            'discount_price', 'discount_end_date', 'current_price',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_price']

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_current_price(self, obj):
        return obj.get_current_price()


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'payment_type', 'discipline', 'lesson', 
            'amount', 'status', 'payment_method', 'transaction_id',
            'created_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'transaction_id',
            'created_at', 'completed_at'
        ]


class CreatePaymentSerializer(serializers.Serializer):
    """
    Тут заполняем данные для нового платежа.
    """
    payment_type = serializers.ChoiceField(
        choices=Payment.PAYMENT_TYPE_CHOICES,
        help_text="Тип платежа: 'discipline' для покупки дисциплины, 'lesson' для покупки урока"
    )
    discipline_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID дисциплины (обязательно для payment_type='discipline')"
    )
    lesson_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID урока (обязательно для payment_type='lesson')"
    )
    payment_method = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Способ оплаты"
    )

    def validate(self, data):
        payment_type = data.get('payment_type')
        discipline_id = data.get('discipline_id')
        lesson_id = data.get('lesson_id')

        if payment_type == 'discipline':
            if not discipline_id:
                raise serializers.ValidationError(
                    "Для покупки дисциплины необходимо указать discipline_id"
                )
            if lesson_id:
                raise serializers.ValidationError(
                    "Для покупки дисциплины не нужно указывать lesson_id"
                )
        elif payment_type == 'lesson':
            if not lesson_id:
                raise serializers.ValidationError(
                    "Для покупки урока необходимо указать lesson_id"
                )
            if discipline_id:
                raise serializers.ValidationError(
                    "Для покупки урока не нужно указывать discipline_id"
                )

        return data


class PurchasedContentSerializer(serializers.ModelSerializer):
    discipline_details = DisciplineSerializer(source='discipline', read_only=True)
    lesson_details = LessonSerializer(source='lesson', read_only=True)
    
    class Meta:
        model = PurchasedContent
        fields = [
            'id', 'user', 'discipline', 'lesson', 'discipline_details', 
            'lesson_details', 'payment', 'purchased_at'
        ]
        read_only_fields = ['id', 'user', 'payment', 'purchased_at']


class PaymentStatusSerializer(serializers.Serializer):
    """
    Тут проверяем статус платежа.
    """
    transaction_id = serializers.CharField(help_text="ID транзакции для проверки статуса")


class YooKassaWebhookSerializer(serializers.Serializer):
    """
    Сериализатор для тела запроса webhook ЮKassa.
    Используется для документации API.
    """
    # Поскольку структура вебхука может быть сложной и динамичной,
    # мы используем DictField для общей документации.
    # Для более детальной валидации потребуется более сложный сериализатор
    # или явное определение полей, если это критично.
    type = serializers.CharField(help_text="Тип уведомления (например, 'notification')")
    event = serializers.CharField(help_text="Событие (например, 'payment.succeeded')")
    object = serializers.DictField(help_text="Объект, связанный с событием (например, данные о платеже)")