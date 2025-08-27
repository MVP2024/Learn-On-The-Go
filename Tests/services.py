from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from Tests.models import QuizAttempt, Choice, Question, Answer

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
            chosen_answers = Choice.objects.filter(quiz_attempt=attempt, question=question)

            if question.is_multiple:
                correct_answers_for_question = set(
                    question.answers.filter(is_correct=True).values_list('id', flat=True)
                )
                chosen_answer_ids_for_question = set(
                    chosen_answers.values_list('answer__id', flat=True)
                )

                # Проверяем, что все выбранные ответы правильные И что все правильные ответы были выбраны
                if correct_answers_for_question == chosen_answer_ids_for_question:
                    total_score += 1
            else:
                # Для вопросов с одним выбором
                # Если выбрано несколько ответов для вопроса с одним выбором, это ошибка, балл не начисляется
                if chosen_answers.count() == 1 and chosen_answers.first().answer.is_correct:
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
        Обрабатываем ответы студента.
        """
        # Очищаем предыдущие выборы для этой попытки
        Choice.objects.filter(quiz_attempt=attempt).delete()

        for item in user_answers_data:
            question_id = item['question_id']
            chosen_answer_ids = item['chosen_answer_ids']

            try:
                question = Question.objects.get(id=question_id, test=attempt.quiz)
            except Question.DoesNotExist:
                raise serializers.ValidationError(f"Вопрос с ID {question_id} не найден в этом тесте.")

            if question.is_multiple:
                valid_answers = Answer.objects.filter(question=question, id__in=chosen_answer_ids)
                if valid_answers.count() != len(chosen_answer_ids):
                    raise serializers.ValidationError(
                        f"Один или несколько выбранных ответов для вопроса {question_id} недействительны."
                    )
                for answer_id in chosen_answer_ids:
                    answer_instance = Answer.objects.get(id=answer_id) # answer_instance гарантированно существует благодаря проверке valid_answers
                    Choice.objects.create(
                        user=attempt.user,
                        question=question,
                        answer=answer_instance,
                        quiz_attempt=attempt
                    )
            else:
                if len(chosen_answer_ids) > 1:
                    raise serializers.ValidationError(f"Вопрос {question_id} допускает только один вариант ответа.")
                try:
                    answer_instance = Answer.objects.get(id=chosen_answer_ids[0], question=question)
                    Choice.objects.create(
                        user=attempt.user,
                        question=question,
                        answer=answer_instance,
                        quiz_attempt=attempt
                    )
                except Answer.DoesNotExist:
                    raise serializers.ValidationError(f"Выбранный ответ для вопроса {question_id} недействителен.")

        QuizAttemptService.calculate_score_for_attempt(attempt)