from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from Exercises.models import Answer, Choice, Question, QuizAttempt, Test


class QuizAttemptService:
    @staticmethod
    @transaction.atomic
    def calculate_score_for_attempt(attempt: QuizAttempt):
        """
        Считаем баллы за попытку.
        """
        total_score = 0
        quiz_questions = attempt.quiz.questions.all()

        for question in quiz_questions:
            chosen_answers = Choice.objects.filter(
                quiz_attempt=attempt, question=question
            )

            if question.is_multiple:
                correct_answers_for_question = set(
                    question.answers.filter(is_correct=True).values_list(
                        "id", flat=True
                    )
                )
                chosen_answer_ids_for_question = set(
                    chosen_answers.values_list("answer__id", flat=True)
                )

                # Проверяем, что все выбранные ответы правильные И что все правильные ответы были выбраны
                if correct_answers_for_question == chosen_answer_ids_for_question:
                    total_score += 1
            else:
                # Для вопросов с одним выбором
                # Если выбрано несколько ответов для вопроса с одним выбором, это ошибка, балл не начисляется
                if (
                    chosen_answers.count() == 1
                    and chosen_answers.first().answer.is_correct
                ):
                    total_score += 1

        attempt.score = total_score
        attempt.is_completed = True
        attempt.end_time = timezone.now()
        attempt.save()
        return total_score

    @staticmethod
    @transaction.atomic
    def submit_test_attempt(attempt: QuizAttempt, user_answers_data: list):
        """
        Обрабатываем ответы студента: сохраняем выборы (Choice) и подсчитываем итоговый score.

        Возвращает итоговый score (int).
        """
        # Очищаем предыдущие выборы для этой попытки
        Choice.objects.filter(quiz_attempt=attempt).delete()

        for item in user_answers_data:
            question_id = item["question_id"]
            chosen_answer_ids = item["chosen_answer_ids"]

            try:
                question = Question.objects.get(id=question_id, test=attempt.quiz)
            except Question.DoesNotExist:
                raise serializers.ValidationError(
                    f"Вопрос с ID {question_id} не найден в этом тесте."
                )

            if question.is_multiple:
                valid_answers = Answer.objects.filter(
                    question=question, id__in=chosen_answer_ids
                )
                if valid_answers.count() != len(chosen_answer_ids):
                    raise serializers.ValidationError(
                        f"Один или несколько выбранных ответов для вопроса {question_id} недействительны."
                    )
                for answer_id in chosen_answer_ids:
                    answer_instance = Answer.objects.get(id=answer_id)
                    Choice.objects.create(
                        user=attempt.user,
                        question=question,
                        answer=answer_instance,
                        quiz_attempt=attempt,
                    )
            else:
                if len(chosen_answer_ids) > 1:
                    raise serializers.ValidationError(
                        f"Вопрос {question_id} допускает только один вариант ответа."
                    )
                if not chosen_answer_ids:
                    raise serializers.ValidationError(
                        f"Не выбран ни один ответ для вопроса {question_id}"
                    )
                try:
                    answer_instance = Answer.objects.get(
                        id=chosen_answer_ids[0], question=question
                    )
                    Choice.objects.create(
                        user=attempt.user,
                        question=question,
                        answer=answer_instance,
                        quiz_attempt=attempt,
                    )
                except Answer.DoesNotExist:
                    raise serializers.ValidationError(
                        f"Выбранный ответ для вопроса {question_id} недействителен."
                    )

        # Подсчитываем баллы и помечаем попытку как завершённую
        score = QuizAttemptService.calculate_score_for_attempt(attempt)
        return score


def _accessible_tests_for_student(user):
    """
    Возвращает queryset Test, доступных студенту только в случае выполнения условий:
    - Тест, привязанный к конкретному уроку (test.lesson != None)
    — доступен только если студент завершил этот урок.
    - Тест, привязанный к дисциплине (test.lesson == None)
    — доступен только если студент завершил все уроки этой дисциплины.
    Причины: студенты не должны иметь доступ к тестам сразу после покупки — только после прохождения урока/дисциплины.
    """
    from django.db.models import Count, F, Q

    from Disciplines.models import Discipline
    from Lessons.models import UserLessonProgress

    completed_lessons = UserLessonProgress.objects.filter(
        user=user, is_completed=True
    ).values_list("lesson_id", flat=True)
    completed_disciplines_qs = (
        Discipline.objects.annotate(
            total_lessons=Count("lessons", distinct=True),
            completed_lessons=Count(
                "lessons__user_progresses",
                filter=Q(
                    lessons__user_progresses__user=user,
                    lessons__user_progresses__is_completed=True,
                ),
                distinct=True,
            ),
        )
        .filter(total_lessons__gt=0, total_lessons=F("completed_lessons"))
        .values_list("id", flat=True)
    )
    qs = Test.objects.filter(
        Q(lesson_id__in=completed_lessons)
        | Q(lesson__isnull=True, discipline_id__in=completed_disciplines_qs)
    ).distinct()
    return qs
