from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

from Users.tasks import notify_superusers_about_admin_key_request, send_admin_key_email

User = get_user_model()


class UsersTasksTests(TestCase):
    """Проверяем, что задачи отправляют письма в соответствии с ролью."""

    def setUp(self):
        # Создаём суперпользователя для notify_superusers_about_admin_key_request
        self.super = User.objects.create_user(
            email="su@a.aa", password="pw", is_superuser=True, is_staff=True
        )
        self.user_admin = User.objects.create_user(
            email="targ@a.aa", password="pw", role="admin"
        )

    def test_send_admin_key_email_sends_for_admin_and_moderator(self):
        """send_admin_key_email должен отправлять письмо для ролей admin/moderator."""
        mail.outbox.clear()
        # вызываем задачу напрямую (в тестах CELERY_ALWAYS_EAGER True => delay выполняет сразу)
        send_admin_key_email.delay(self.user_admin.email, "SOMEKEY", "admin")
        # проверяем что письмо ушло
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn("Ваш административный ключ", msg.subject)
        self.assertIn("SOMEKEY", msg.body)

    def test_notify_superusers_about_admin_key_request_sends_to_superusers(self):
        """notify_superusers_about_admin_key_request отправляет письмо всем суперпользователям."""
        mail.outbox.clear()
        notify_superusers_about_admin_key_request.delay("requester@a.aa", "admin")
        self.assertGreaterEqual(len(mail.outbox), 1)
        recipients = mail.outbox[0].to
        self.assertIn(self.super.email, recipients)
