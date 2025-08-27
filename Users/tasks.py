from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings


User = get_user_model()

@shared_task
def send_admin_key_email(user_email, admin_key, role):
    """
    Отправляет email пользователю с админ-ключом и информацией о его роли.
    """
    subject = f"Ваш доступ к системе LearningPlatform - роль: {role.capitalize()}"

    if role == "moderator":
        message_body = (
            f"Здравствуйте!\n\nВы были добавлены в группу модераторов LearningPlatform.\n"
            f"Ваш административный ключ: {admin_key}\n\n"
            f"Используйте этот ключ для доступа к функциям модератора.\n"
            f"Если у вас возникнут вопросы, обращайтесь в службу поддержки."
        )
    elif role == "admin":
        message_body = (
            f"Здравствуйте!\n\nВы были добавлены в группу администраторов LearningPlatform.\n"
            f"Ваш административный ключ: {admin_key}\n\n"
            f"Используйте этот ключ для доступа к функциям администратора.\n"
            f"Будьте внимательны при работе с критическими функциями.\n"
            f"Если у вас возникнут вопросы, обращайтесь в службу поддержки."
        )
    else:
        # Для других ролей можно не отправлять или отправить другое сообщение
        return

    from_email = settings.DEFAULT_FROM_EMAIL

    send_mail(
        subject,
        message_body,
        from_email,
        [user_email],
        fail_silently=False,
    )


@shared_task
def notify_superusers_about_admin_key_request(user_email, user_role):
    """
    Отправляет уведомление всем суперпользователям о запросе админ-ключа.
    """
    superusers = User.objects.filter(is_superuser=True, is_active=True)
    if not superusers.exists():
        return

    superuser_emails = [su.email for su in superusers]

    subject = f"Запрос на получение админ-ключа от пользователя {user_email} (роль: {user_role})"
    message_body = (
        f"Пользователь {user_email} с ролью {user_role} запросил административный ключ.\n"
        f"Пожалуйста,  войдите в панель администратора и проверьте запрос и предоставьте ключ, "
        f"если это необходимо: {settings.BASE_URL}/admin/Users/user/"
        # Здесь можно добавить ссылку на конкретную страницу пользователя в админке, если есть такая.
    )
    from_email = settings.DEFAULT_FROM_EMAIL

    send_mail(
        subject,
        message_body,
        from_email,
        superuser_emails,
        fail_silently=False,
    )
