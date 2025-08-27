from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager

from utils.image_validators import validate_image_file


class CustomUserManager(UserManager):
    """
    Менеджер для наших пользователей. Использует email вместо username.
    """

    def _create_user(self, email, password, **extra_fields):
        """
        Создаем пользователя.
        """
        if not email:
            raise ValueError('Необходимо указать адрес электронной почты')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """
        Создаем обычного пользователя.
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Создаем админа.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Наш пользователь. Логинится по email вместо username.
    """
    ROLE_CHOICES = (
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
        ('admin', 'Администратор'),
        ('moderator', 'Модератор'),
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='student',
        verbose_name="Роль пользователя"
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Электронная почта",
        help_text="Укажите свой email"
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Фамилия",
        help_text="Введите фамилию"
    )
    first_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Имя",
        help_text="Введите имя"
    )
    patronymic = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Отчество",
        help_text="Введите отчество"
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата рождения",
        help_text="Введите дату рождения"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Телефон",
        help_text="В формате +79991234567"
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name="Аватарка",
        help_text="Загрузите аватарку",
        validators=[validate_image_file]
    )
    is_admin_key_required = models.BooleanField(
        default=False,
        verbose_name="Требуется админ-ключ для входа",
        help_text="Если True, пользователь должен будет предоставить уникальный админ-ключ для входа/регистрации с ролью администратора/модератора."
    )
    # Добавляем поле для отслеживания, был ли первый вход с ключом
    has_logged_in_with_key = models.BooleanField(
        default=False,
        verbose_name="Входил с админ-ключом",
        help_text="Показывает, совершал ли пользователь вход с использованием админ-ключа."
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    username = None

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='user_groups',
        blank=True,
        help_text='Группы, к которым принадлежит пользователь. Пользователь получит все разрешения, предоставленные каждой из его групп.',
        verbose_name='Группы',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='user_user_permissions',
        blank=True,
        help_text='Специфические разрешения для этого пользователя.',
        verbose_name='Права пользователя',
    )

    @property
    def full_name(self):
        """
        Получаем полное имя.
        """
        full_name = f"{self.first_name} {self.last_name}".strip()
        if not full_name and self.email:
            return self.email
        return full_name

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
