from django.db import models

from Users.models import User


class Student(models.Model):
    COURSE_CHOICES = [(i, f"{i} курс") for i in range(1, 7)]
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    course = models.PositiveSmallIntegerField(
        choices=COURSE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Курс",
        help_text="Выберите курс обучения",
    )

    def __str__(self):
        return f"{self.user.full_name} - Студент"

    class Meta:
        verbose_name = "Студент"
        verbose_name_plural = "Студенты"
