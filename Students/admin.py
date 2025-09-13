from django.contrib import admin

from Students.models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("user", "course")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_filter = ("course",)
