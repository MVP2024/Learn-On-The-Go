from rest_framework import serializers

from .models import Answer, Choice, Question, QuizAttempt, Test


class AnswerSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.all(), write_only=True
    )

    class Meta:
        model = Answer
        fields = ["id", "text", "is_correct", "question"]
        read_only_fields = ["id"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            data.pop("is_correct", None)
            return data

        user = request.user
        if (
            user.is_superuser
            or user.groups.filter(name__in=["admin", "moderator"]).exists()
            or user.groups.filter(name="teacher").exists()
        ):
            return data

        try:
            test = instance.question.test
            if getattr(test, "owner", None) == user:
                return data
        except Exception:
            test = None

        if test is None:
            data.pop("is_correct", None)
            return data

        completed = QuizAttempt.objects.filter(
            user=user, quiz=test, is_completed=True
        ).exists()
        if not completed:
            data.pop("is_correct", None)
        return data


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "test", "text", "question_order", "is_multiple", "answers"]
        read_only_fields = ["id", "answers"]


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = [
            "id",
            "title",
            "description",
            "discipline",
            "lesson",
            "section",
            "owner",
            "created_at",
            "updated_at",
            "questions",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at", "questions"]


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "user", "question", "answer", "quiz_attempt", "created_at"]
        read_only_fields = ["id", "created_at"]


class QuizAttemptSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            "id",
            "user",
            "quiz",
            "start_time",
            "end_time",
            "score",
            "is_completed",
            "choices",
        ]
        read_only_fields = [
            "id",
            "user",
            "quiz",
            "start_time",
            "end_time",
            "score",
            "is_completed",
            "choices",
        ]


class SubmitTestSerializer(serializers.Serializer):
    """
    Ожидает список ответов в формате:
    answers: [
      {"question_id": 1, "chosen_answer_ids": [1, 2]},
      {"question_id": 2, "chosen_answer_ids": [3]}
    ]
    """

    answers = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate(self, attrs):
        answers = attrs.get("answers")
        if not isinstance(answers, list) or len(answers) == 0:
            raise serializers.ValidationError(
                "Поле 'answers' должно быть непустым списком."
            )
        for item in answers:
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    "Каждый элемент в 'answers' должен быть объектом."
                )
            if "question_id" not in item or "chosen_answer_ids" not in item:
                raise serializers.ValidationError(
                    "Каждый объект должен содержать 'question_id' и 'chosen_answer_ids'."
                )
            if not isinstance(item["chosen_answer_ids"], list):
                raise serializers.ValidationError(
                    "'chosen_answer_ids' должно быть списком идентификаторов."
                )
            # Убеждаемся, что идентификаторы являются целыми
            try:
                item["question_id"] = int(item["question_id"])  # можем вызвать
                item["chosen_answer_ids"] = [int(x) for x in item["chosen_answer_ids"]]
            except Exception:
                if len(item["chosen_answer_ids"]) == 0:
                    raise serializers.ValidationError(
                        f"chosen_answer_ids не может быть пустым для question_id {item.get('question_id')}"
                    )
        return attrs
