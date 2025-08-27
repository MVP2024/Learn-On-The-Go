from django.contrib import admin

from Teachers.models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    filter_horizontal = ('disciplines',)
