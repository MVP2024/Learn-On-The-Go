from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .tasks import send_admin_key_email
from Admin.models import AdminKey
from Students.models import Student
from Teachers.models import Teacher
from .models import User
from django.contrib.auth.models import Group
from utils.mixins import ProfanityFilterMixin


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Кастомный сериализатор для получения JWT токена,
    использующий email вместо username.
    """

    username_field = "email"

    def validate(self, attrs):
        # Вызываем родительский метод для стандартной аутентификации email/password
        data = super().validate(attrs)
        return data


class AdminKeyLoginSerializer(serializers.Serializer):
    """
    Сериализатор для входа с использованием административного ключа.
    """

    email = serializers.EmailField(help_text="Email пользователя.")
    password = serializers.CharField(write_only=True, help_text="Пароль пользователя.")
    admin_key = serializers.CharField(
        write_only=True,
        help_text="Административный ключ для первого входа.",
        required=True,
    )

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        admin_key = attrs.get("admin_key")

        if not email or not password or not admin_key:
            raise serializers.ValidationError("Email, пароль и админ-ключ обязательны.")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Неверные учетные данные.")

        if not user.check_password(password):
            raise serializers.ValidationError("Неверные учетные данные.")

        if (
            user.role not in ["admin", "moderator"]
            or not user.is_admin_key_required
            or user.has_logged_in_with_key
        ):
            raise serializers.ValidationError(
                "Для вашей роли или статуса административный ключ не требуется или уже был использован."
            )

        try:
            admin_key_obj = AdminKey.objects.get(
                user=user, key=admin_key, is_active=True
            )
            user.has_logged_in_with_key = True
            user.save()
            admin_key_obj.is_active = False
            admin_key_obj.save()
        except AdminKey.DoesNotExist:
            raise serializers.ValidationError("Неверный или неактивный админ-ключ.")

        # Успешная аутентификация, возвращаем пользователя
        self.user = user
        return {}


class RegisterSerializer(ProfanityFilterMixin, serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, help_text="Пароль должен быть быть надежным."
    )
    role = serializers.ChoiceField(
        choices=User.ROLE_CHOICES,
        help_text="Выберите роль пользователя: 'student', 'teacher', 'moderator' или 'admin'."
        "Пользователи с ролями 'moderator' и 'admin' будут созданы, но потребуют активации администратором для получения ключа."
        "Пользователи с ролями 'student' и 'teacher' могут зарегистрироваться без ключа.",
        error_messages={
            "invalid_choice": f'Указанная роль "{input}" не является допустимой. Пожалуйста, выберите роль пользователя.'
        },
    )

    class Meta:
        model = User
        fields = ["email", "password", "role", "first_name", "last_name", "patronymic"]
        extra_kwargs = {
            "email": {
                "error_messages": {
                    "unique": "Пользователь с таким адресом электронной почты уже зарегистрирован."
                }
            },
        }
        profanity_fields = ["first_name", "last_name", "patronymic"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return attrs

    def create(self, validated_data):
        role = validated_data.pop("role")
        user = User.objects.create_user(**validated_data)
        user.role = role

        if role in ["admin", "moderator"]:
            # При регистрации админов/модераторов, им пока не выдается ключ.
            # Ключ будет генерироваться и выдаваться суперпользователем позже.
            user.is_admin_key_required = (
                True  # Флаг, что этому пользователю ключ потребуется
            )
            user.is_active = (
                False  # Пользователь неактивен до выдачи ключа суперпользователем
            )
            user.save()
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.add(group)
            # Отправляем уведомление суперпользователю о новой заявке, если нужно
            # send_email_to_superusers_about_new_admin_request(user.email, user.role)
        else:
            user.save()  # Сохраняем обычного пользователя
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.add(group)
            if role == "teacher":
                Teacher.objects.create(user=user)
            elif role == "student":
                Student.objects.create(user=user)

        return user


class UserProfilePublicSerializer(ProfanityFilterMixin, serializers.ModelSerializer):
    """
    Сериализатор для публичного просмотра профиля пользователя.
    Отображает только общую информацию.
    """

    disciplines_taught = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["avatar", "last_name", "first_name", "disciplines_taught"]
        profanity_fields = ["first_name", "last_name"]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_disciplines_taught(self, obj):
        try:
            teacher_profile = obj.teacher
            return [
                discipline.title for discipline in teacher_profile.disciplines.all()
            ]
        except Teacher.DoesNotExist:
            return None


class UserProfilePrivateSerializer(ProfanityFilterMixin, serializers.ModelSerializer):
    """
    Сериализатор для приватного просмотра/редактирования собственного профиля.
    Отображает всю информацию, кроме пароля.
    """

    class Meta:
        model = User
        fields = [
            "email",
            "last_name",
            "first_name",
            "patronymic",
            "date_of_birth",
            "phone_number",
            "avatar",
            "is_admin_key_required",
            "has_logged_in_with_key",
        ]
        read_only_fields = [
            "email",
            "is_admin_key_required",
            "has_logged_in_with_key",
        ]  # Запрещаем изменение email и is_admin_key_required после регистрации
        profanity_fields = ["first_name", "last_name", "patronymic"]


class RequestAdminKeySerializer(serializers.Serializer):
    """
    Сериализатор для запроса админ-ключа.
    """

    email = serializers.EmailField(
        help_text="Email пользователя, для которого запрашивается админ-ключ."
    )
