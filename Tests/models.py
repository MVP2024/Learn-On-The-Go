from django.db import models
from Disciplines.models import Discipline, Section
from Users.models import User


class Test(models.Model):
    title = models.CharField(
        max_length=255,
        verbose_name="Название теста",
        help_text="Введите название теста. Максимальная длина - 255 символов."
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Описание теста",
        help_text="Введите описание теста."
    )
    discipline = models.ForeignKey(
        Discipline,
        on_delete=models.CASCADE,
        related_name='tests',
        verbose_name="Предмет",
        help_text="Дисциплина, к которой относится тест."
    )
    lesson = models.ForeignKey(
        'Lessons.Lesson',
        on_delete=models.SET_NULL,  # SET_NULL, если тест может существовать без урока
        related_name='tests',
        verbose_name="Урок",
        help_text="Урок, к которому относится тест (необязательно).",
        null=True,
        blank=True
    )
    section = models.ForeignKey( # Добавляем связь с разделом
        Section,
        on_delete=models.SET_NULL, # или models.CASCADE, в зависимости от логики
        related_name='tests',
        verbose_name="Раздел",
        null=True,
        blank=True,
        help_text="Раздел дисциплины, к которому относится тест (необязательно)."
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Владелец теста",
        help_text="Пользователь, создавший тест.",
        null=True, # Может быть null, если создано модератором
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
        help_text="Дата и время создания теста."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
        help_text="Дата и время последнего обновления теста."
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Тест"
        verbose_name_plural = "Тесты"


class Question(models.Model):
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="Тест",
        help_text="Тест, к которому относится вопрос."
    )
    text = models.TextField(
        verbose_name="Текст вопроса",
        help_text="Введите текст вопроса."
    )
    question_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Номер вопроса",
        help_text="Порядковый номер вопроса в тесте (1, 2, 3...)",
        db_index=True
    )
    is_multiple = models.BooleanField(
        default=False,
        verbose_name="Множественный выбор",
        help_text="Если выбрано, пользователь может выбрать несколько вариантов ответа."
    )

    def __str__(self):
        return f"Вопрос {self.question_order} для теста '{self.test.title}': {self.text[:50]}..."

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
        ordering = ['question_order']

class Answer(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name="Вопрос",
        help_text="Вопрос, к которому относится ответ."
    )
    text = models.CharField(
        max_length=255,
        verbose_name="Текст ответа",
        help_text="Введите текст ответа. Максимальная длина - 255 символов."
    )
    is_correct = models.BooleanField(
        default=False,
        verbose_name="Правильный ответ",
        help_text="Указывает, является ли этот ответ правильным."
    )

    def __str__(self):
        return f"Ответ на вопрос '{self.question.text[:50]}...': {self.text}"

    class Meta:
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"

class QuizAttempt(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='quiz_attempts',
        verbose_name='Пользователь',
        help_text='Пользователь, проходящий тест.'
    )
    quiz = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name='Тест',
        help_text='Тест, который проходит пользователь.'
    )
    start_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время начала',
        help_text='Дата и время начала попытки.'
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время окончания',
        help_text='Дата и время окончания попытки.'
    )
    score = models.IntegerField(
        default=0,
        verbose_name='Набранные баллы',
        help_text='Количество набранных баллов за тест.'
    )
    is_completed = models.BooleanField(
        default=False,
        verbose_name='Попытка завершена',
        help_text='Флаг, указывающий, завершена ли попытка.'
    )

    def __str__(self):
        return f"{self.user.email} - Попытка теста '{self.quiz.title}'"

    class Meta:
        verbose_name = 'Попытка прохождения теста'
        verbose_name_plural = 'Попытки прохождения тестов'
        # unique_together = ('user', 'quiz') # Пользователь может иметь несколько попыток


class Choice(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        help_text='Пользователь, сделавший выбор.'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        verbose_name='Вопрос',
        help_text='Вопрос, на который дан ответ.'
    )
    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        verbose_name='Выбранный ответ',
        help_text='Выбранный пользователем вариант ответа.'
    )
    quiz_attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='choices',
        verbose_name='Попытка теста',
        help_text='Попытка прохождения теста, к которой относится этот выбор.'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время выбора',
        help_text='Дата и время, когда был сделан выбор.'
    )

    def __str__(self):
        return f"Выбор {self.user.email} на вопрос '{self.question.text[:30]}...' в тесте '{self.quiz_attempt.quiz.title}'"

    class Meta:
        verbose_name = 'Выбор ответа'
        verbose_name_plural = 'Выборы ответов'
        unique_together = ('user', 'question', 'quiz_attempt', 'answer')


class QuizCategory(models.Model):
    """
    Категории тестов.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Название категории",
        help_text="Например, 'Тест по главе 3'"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория теста"
        verbose_name_plural = "Категории тестов"


class QuestionHint(models.Model):
    """
    Подсказки для студентов.
    """
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        related_name='hint',
        verbose_name="Вопрос",
        help_text="Вопрос, к которому относится подсказка."
    )
    text = models.TextField(
        verbose_name="Текст подсказки",
        help_text="Введите текст подсказки, которая будет показана после ошибки."
    )

    def __str__(self):
        return f"Подсказка для вопроса: {self.question.text[:50]}..."

    class Meta:
        verbose_name = "Подсказка к вопросу"
        verbose_name_plural = "Подсказки к вопросам"