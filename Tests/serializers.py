from rest_framework import serializers

from Disciplines.models import Discipline
from .models import Test, Question, Answer, QuizAttempt, Choice, QuestionHint, QuizCategory
from Users.serializers import UserProfilePublicSerializer
from utils.mixins import ProfanityFilterMixin
from drf_spectacular.utils import extend_schema_field


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'text', 'is_correct']
        read_only_fields = ['id'] # ID должен быть доступен для выбора ответов
        extra_kwargs = {
            'is_correct': {'help_text': 'Отметьте, если это правильный ответ.'}
        }


class QuestionHintSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionHint
        fields = ['id', 'text']
        read_only_fields = ['id']


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True)  # Вложенный сериализатор для ответов
    hint = QuestionHintSerializer(read_only=True)  # Вложенный сериализатор для подсказок

    class Meta:
        model = Question
        fields = ['id', 'text', 'question_order', 'answers', 'hint']
        read_only_fields = ['id']
        extra_kwargs = {
            'question_order': {'help_text': 'Порядковый номер вопроса в тесте.'}
        }

class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = ['id', 'user', 'quiz', 'start_time', 'end_time', 'score', 'is_completed']
        read_only_fields = ['id', 'user', 'quiz', 'start_time', 'end_time', 'score', 'is_completed']


class QuizCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizCategory
        fields = ['id', 'name']
        read_only_fields = ['id']


class QuizSerializer(ProfanityFilterMixin, serializers.ModelSerializer):
    owner = UserProfilePublicSerializer(read_only=True)
    discipline = serializers.SlugRelatedField(
        slug_field='title',
        queryset=Discipline.objects.all(),
        help_text="Название дисциплины, к которой относится тест (например: 'Математика')."
    )
    question_count = serializers.SerializerMethodField()
    user_attempt_progress = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ['id', 'title', 'description', 'discipline', 'owner',
                  'created_at', 'updated_at', 'question_count', 'user_attempt_progress']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
        profanity_fields = ['title', 'description']

    @extend_schema_field(serializers.IntegerField)
    def get_question_count(self, obj):
        return obj.questions.count()

    @extend_schema_field(QuizAttemptSerializer)
    def get_user_attempt_progress(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Получаем последнюю незавершенную попытку
            try:
                attempt = QuizAttempt.objects.filter(user=request.user, quiz=obj).order_by('-start_time').first()
                if attempt:
                    return QuizAttemptSerializer(attempt).data
            except QuizAttempt.DoesNotExist:
                return None
        return None


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'question', 'answer']
        read_only_fields = ['id']


class SubmitTestSerializer(serializers.Serializer):
    """
    Сериализатор для приема ответов пользователя на тест.
    Ожидает список объектов, где каждый объект содержит 'question_id' и 'chosen_answer_ids'.
    """
    # Список вопросов, каждый из которых содержит ID вопроса и список выбранных ID ответов
    answers = serializers.ListField(
        child=serializers.DictField(
            child=serializers.ListField(
                child=serializers.IntegerField(),
                min_length=1,
                allow_empty=False
            ),
            # Key 'question_id' for question ID, Value 'chosen_answer_ids' for list of chosen answer IDs
            # Example: {"question_id": 1, "chosen_answer_ids": [101, 103]}
        ),
        min_length=1,
        allow_empty=False
    )
    @staticmethod
    def validate_answers(value):
        """
        Проверка корректности данных ответов.
        """
        if not value:
            raise serializers.ValidationError("Необходимо предоставить хотя бы один ответ.")

        for item in value:
            if 'question_id' not in item or 'chosen_answer_ids' not in item:
                raise serializers.ValidationError(
                    "Каждый ответ должен содержать 'question_id' и 'chosen_answer_ids'."
                )
            if not isinstance(item['question_id'], int):
                raise serializers.ValidationError("'question_id' должен быть целым числом.")
            if not isinstance(item['chosen_answer_ids'], list) or not all(isinstance(x, int) for x in item['chosen_answer_ids']):
                raise serializers.ValidationError("'chosen_answer_ids' должен быть списком целых чисел.")
        return value
