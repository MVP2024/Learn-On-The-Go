from django.contrib import admin

from Disciplines.models import Discipline, Section


class SectionInline(admin.TabularInline):
    model = Section
    extra = 1
    show_change_link = True


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "preview", "order")
    search_fields = ("title", "description", "owner__email")
    list_filter = ("owner",)
    inlines = [SectionInline]
