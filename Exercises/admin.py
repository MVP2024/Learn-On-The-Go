from django.contrib import admin

from Exercises.models import (
    Answer,
    Choice,
    Question,
    QuestionHint,
    QuizAttempt,
    QuizCategory,
    Test,
)


class AnswerInline(admin.TabularInline):
    """
    Позволяет редактировать ответы прямо на странице вопроса.
    """

    model = Answer
    extra = 1  # Дополнительное пустое поле для нового ответа


class QuestionInline(admin.TabularInline):
    """
    Позволяет редактировать вопросы прямо на странице теста.
    """

    model = Question
    extra = 1
    show_change_link = True  # Разрешает переход на страницу вопроса из инлайна


class ChoiceInline(admin.TabularInline):
    """
    Позволяет просматривать выборы пользователя в рамках попытки.
    """

    model = Choice
    extra = 0
    readonly_fields = ("user", "question", "answer")


class QuestionHintInline(admin.StackedInline):
    """
    Позволяет редактировать подсказку прямо на странице вопроса.
    """

    model = QuestionHint
    extra = 0
    max_num = 1  # Только одна подсказка на вопрос


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ("title", "discipline", "owner", "created_at", "updated_at")
    search_fields = ("title", "description", "discipline__title", "owner__email")
    list_filter = ("discipline", "owner")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "test", "question_order")
    search_fields = ("text", "test__title")
    list_filter = ("test", "is_multiple")
    inlines = [AnswerInline]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("text", "question", "is_correct")
    list_filter = ("is_correct", "question__test")
    search_fields = ("text", "question__text")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "quiz", "score", "is_completed", "start_time", "end_time")
    list_filter = ("is_completed", "quiz", "user")
    search_fields = ("user__email", "quiz__title")
    inlines = [ChoiceInline]
    readonly_fields = ("score", "start_time", "end_time")


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "answer", "quiz_attempt", "created_at")
    list_filter = ("quiz_attempt__quiz", "question", "user")
    search_fields = ("user__email", "question__text", "answer__text")
    readonly_fields = ("created_at",)


@admin.register(QuizCategory)
class QuizCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(QuestionHint)
class QuestionHintAdmin(admin.ModelAdmin):
    list_display = ("question", "text")
    search_fields = ("question__text", "text")
