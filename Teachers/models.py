from django.db import models

from Users.models import User


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    disciplines = models.ManyToManyField(
        "Disciplines.Discipline",
        verbose_name="Предметы",
        help_text="Дисциплины, которые преподает этот учитель.",
    )

    def __str__(self):
        return f"{self.user.full_name} - Преподаватель"

    class Meta:
        verbose_name = "Преподаватель"
        verbose_name_plural = "Преподаватели"
