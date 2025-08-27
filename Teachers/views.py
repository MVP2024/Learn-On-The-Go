# from rest_framework import viewsets
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from Disciplines.models import Discipline
# from Lessons.models import Lesson
# from Tests.models import Test
# from Disciplines.serializers import DisciplineSerializer
# from Lessons.serializers import LessonSerializer
# from Tests.serializers import QuizSerializer
# from Users.permissions import IsTeacher
# from drf_spectacular.utils import extend_schema
#
# @extend_schema(tags=['Учителя: Дисциплины, Уроки, Тесты'])
# class TeacherRelatedContentViewSet(viewsets.GenericViewSet):
#     """
#     ViewSet для получения дисциплин, уроков и тестов, связанных с текущим авторизованным учителем.
#     """
#     permission_classes = [IsAuthenticated, IsTeacher]
#
#     def get_queryset(self):
#         # Этот queryset не используется напрямую для списка, но нужен для DRF
#         return Discipline.objects.none()
#
#     @extend_schema(
#         summary="Получить дисциплины текущего учителя",
#         description="Возвращает список дисциплин, владельцем которых является текущий авторизованный учитель.",
#         responses={200: DisciplineSerializer(many=True)}
#     )
#     @action(detail=False, methods=['get'])
#     def my_disciplines(self, request):
#         disciplines = Discipline.objects.filter(owner=request.user)
#         serializer = DisciplineSerializer(disciplines, many=True, context={'request': request})
#         return Response(serializer.data)
#
#     @extend_schema(
#         summary="Получить уроки текущего учителя",
#         description="Возвращает список уроков, владельцем которых является текущий авторизованный учитель.",
#         responses={200: LessonSerializer(many=True)}
#     )
#     @action(detail=False, methods=['get'])
#     def my_lessons(self, request):
#         lessons = Lesson.objects.filter(owner=request.user)
#         serializer = LessonSerializer(lessons, many=True, context={'request': request})
#         return Response(serializer.data)
#
#     @extend_schema(
#         summary="Получить тесты текущего учителя",
#         description="Возвращает список тестов, владельцем которых является текущий авторизованный учитель.",
#         responses={200: QuizSerializer(many=True)}
#     )
#     @action(detail=False, methods=['get'])
#     def my_tests(self, request):
#         tests = Test.objects.filter(owner=request.user)
#         serializer = QuizSerializer(tests, many=True, context={'request': request})
#         return Response(serializer.data)
