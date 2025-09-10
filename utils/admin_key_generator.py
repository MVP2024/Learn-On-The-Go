import os
import secrets

import django

# Настраиваем окружение Django
# этот скрипт запускается как отдельный скрипт, а не как часть Django-приложения, (т.е.не через manage.py),
# а от этого Django этого не знает, где искать настройки, поэтому надо ему подсказать.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction  # Для атомарных операций

from Admin.models import AdminKey  # Импортируем модель AdminKey
from Users.models import User


def generate_key_and_message(user_obj):
    """
    Генерирует уникальный административный ключ и формирует сообщение
    для отправки по email. Параметр называется user_obj чтобы не затенять
    имя `user` из внешней области видимости в других частях файла.
    """
    admin_key = secrets.token_urlsafe(32)

    # Используем полное имя, если доступно, иначе email
    recipient_name = user_obj.full_name if user_obj.full_name else user_obj.email

    message_template = f"""
Привет, {recipient_name}!

Вот ваш сгенерированный административный ключ для регистрации/входа в систему LearningPlatform:

{admin_key}

Пожалуйста, сохраните этот ключ в надежном месте. Он потребуется вам для регистрации или аутентификации с ролью администратора/модератора.

С наилучшими пожеланиями,
Команда LearningPlatform
"""
    return admin_key, message_template


if __name__ == "__main__":
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    print("--- Генератор Административного Ключа ---")
    user_email = input(
        "Введите email пользователя, для которого генерируется ключ (например, admin@example.com): "
    ).strip()

    if not user_email:
        print("Email не может быть пустым. Выход.")
    else:
        try:
            user = User.objects.get(email=user_email)

            if user.role not in ["admin", "moderator"]:
                print(
                    f"Пользователь {user_email} имеет роль '{user.role}', админ-ключ ему не требуется."
                )
            else:
                with transaction.atomic():
                    # Деактивируем все предыдущие активные ключи для этого пользователя
                    AdminKey.objects.filter(user=user, is_active=True).update(
                        is_active=False
                    )

                    generated_key, message = generate_key_and_message(user)

                    # Создаем новую запись AdminKey
                    AdminKey.objects.create(
                        user=user, key=generated_key, is_active=True, email=user.email
                    )

                    # Активируем пользователя, если он неактивен, и устанавливаем флаг is_admin_key_required
                    if not user.is_active or not user.is_admin_key_required:
                        user.is_active = True
                        user.is_admin_key_required = True
                        user.save()

                print("\n--- ГЕНЕРАЦИЯ ЗАВЕРШЕНА ---")
                print(f"Сгенерирован ключ: '{generated_key}'")

                send_email = (
                    input(f"Отправить этот ключ на почту {user_email}? (да/нет): ")
                    .strip()
                    .lower()
                )
                if send_email == "да":
                    try:
                        send_mail(
                            f"Ваш административный ключ для входа в LearningPlatform",
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [user_email],
                            fail_silently=False,
                        )
                        print(f"Ключ успешно отправлен на {user_email}.")
                    except Exception as e:
                        print(f"Не удалось отправить email: {e}")
                else:
                    print("Отправка email отменена.")

                print("\n--- СООБЩЕНИЕ ДЛЯ ПОЛЬЗОВАТЕЛЯ ---")
                print("Это сообщение вы можете отправить пользователю по его email:")
                print(message)
        except User.DoesNotExist:
            print(f"Пользователь с email '{user_email}' не найден.")
        except Exception as e:
            print(f"Произошла ошибка: {e}")
