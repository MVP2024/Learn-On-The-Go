from Exercises.models import Test
from Lessons.models import Lesson


def get_lessons_and_tests_for_discipline(discipline_id):
    """
    Возвращает списки уроков и тестов для указанного предмета.
    """
    lessons = Lesson.objects.filter(discipline_id=discipline_id).order_by(
        "lesson_order"
    )
    tests = Test.objects.filter(discipline_id=discipline_id).order_by("created_at")
    return lessons, tests
