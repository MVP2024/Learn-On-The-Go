"""
Модели для системы платежей.
Здесь хранятся данные о платежах студентов, ценах на курсы и купленном контенте.
Это позволяет студентам покупать дисциплины и уроки.
"""
from django.db import models
from Users.models import User
from Disciplines.models import Discipline
from Lessons.models import Lesson
from decimal import Decimal

class Payment(models.Model):
    """
    Тут хранятся платежи пользователей за уроки и дисциплины.
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидание'),
        ('completed', 'Завершен'),
        ('failed', 'Неудачный'),
        ('refunded', 'Возвращен'),
    ]

    PAYMENT_TYPE_CHOICES = [
        ('discipline', 'Дисциплина'),
        ('lesson', 'Урок'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Пользователь'
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        verbose_name='Тип платежа'
    )
    discipline = models.ForeignKey(
        Discipline,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Дисциплина'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Урок'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма'
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name='Статус платежа'
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Способ оплаты'
    )
    transaction_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        verbose_name='ID транзакции'
    )
    yookassa_payment_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='ID платежа в ЮKassa'
    )
    yookassa_confirmation_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='URL для оплаты в ЮKassa'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата завершения'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']

    def __str__(self):
        if self.payment_type == 'discipline':
            return f"Платеж {self.user.email} за дисциплину {self.discipline.title}"
        else:
            return f"Платеж {self.user.email} за урок {self.lesson.title}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.payment_type == 'discipline' and not self.discipline:
            raise ValidationError('Для типа платежа "дисциплина" необходимо указать дисциплину')
        if self.payment_type == 'lesson' and not self.lesson:
            raise ValidationError('Для типа платежа "урок" необходимо указать урок')


class PurchasedContent(models.Model):
    """
    Тут записывается что студент купил.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='purchased_content',
        verbose_name='Пользователь'
    )
    discipline = models.ForeignKey(
        Discipline,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='purchased_by',
        verbose_name='Купленная дисциплина'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='purchased_by',
        verbose_name='Купленный урок'
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='purchased_content',
        verbose_name='Связанный платеж'
    )
    purchased_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата покупки'
    )

    class Meta:
        verbose_name = 'Купленный контент'
        verbose_name_plural = 'Купленный контент'
        unique_together = [
            ('user', 'discipline'),
            ('user', 'lesson'),
        ]

    def __str__(self):
        if self.discipline:
            return f"{self.user.email} купил дисциплину {self.discipline.title}"
        else:
            return f"{self.user.email} купил урок {self.lesson.title}"


class PriceConfiguration(models.Model):
    """
    Тут хранятся цены на уроки и дисциплины.
    """
    discipline = models.OneToOneField(
        Discipline,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='price_config',
        verbose_name='Дисциплина'
    )
    lesson = models.OneToOneField(
        Lesson,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='price_config',
        verbose_name='Урок'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Цена'
    )
    is_free = models.BooleanField(
        default=False,
        verbose_name='Бесплатно'
    )
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Цена со скидкой'
    )
    discount_end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата окончания скидки'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Конфигурация цены'
        verbose_name_plural = 'Конфигурации цен'

    def __str__(self):
        if self.discipline:
            return f"Цена для дисциплины {self.discipline.title}: {self.get_current_price()}"
        else:
            return f"Цена для урока {self.lesson.title}: {self.get_current_price()}"

    def get_current_price(self):
        """
        Возвращает текущую цену с учетом скидки.
        """
        if self.is_free:
            return Decimal('0.00')
        
        from django.utils import timezone
        if (self.discount_price and 
            self.discount_end_date and 
            timezone.now() <= self.discount_end_date):
            return self.discount_price
        
        return self.price

    def clean(self):
        from django.core.exceptions import ValidationError
        
        if not self.discipline and not self.lesson:
            raise ValidationError('Необходимо указать либо дисциплину, либо урок')
        if self.discipline and self.lesson:
            raise ValidationError('Нельзя указывать одновременно дисциплину и урок')