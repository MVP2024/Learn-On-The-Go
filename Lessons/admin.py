from django.contrib import admin

from Lessons.models import UserLessonProgress, Lesson


class UserLessonProgressInline(admin.TabularInline):
    """
    Позволяет редактировать прогресс урока прямо на странице урока.
    """
    model = UserLessonProgress
    extra = 0
    readonly_fields = ('user', 'watched_duration', 'last_watched_at')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'discipline', 'owner', 'lesson_order', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'discipline__title', 'owner__email')
    list_filter = ('discipline', 'owner')
    inlines = [UserLessonProgressInline]
    ordering = ('discipline', 'lesson_order')


@admin.register(UserLessonProgress)
class UserLessonProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'is_completed', 'watched_duration', 'last_watched_at')
    list_filter = ('is_completed', 'lesson', 'user')
    search_fields = ('user__email', 'lesson__title')
