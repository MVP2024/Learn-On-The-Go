# Руководство по Celery — LearningPlatform

Кратко
- Celery используется для фоновой обработки задач: отправка писем, обработка платежей, периодические задачи и т. п.
- В проекте есть удобный скрипт для dev: python start_celery.py
- В продакшне запускать через systemd / supervisor / контейнеры (docker-compose или kubernetes).

Содержание
- Быстрый запуск (dev)
- Запуск в Docker / продакшн
- Основные настройки
- Частые команды и отладка
- Рекомендации по безопасности

---

1) Быстрый запуск (локально, для разработки)

1. Установите зависимости (если нужно):

```bash
pip install -r requirements.txt
```

2. Убедитесь, что Redis запущен (как брокер). Для локали проще запустить контейнер:

```bash
docker run -d --name lp-redis -p 6379:6379 redis:alpine
# Или локально: redis-server
```

3. Запустите Django (в другом терминале) и скрипт Celery (dev):

```bash
python manage.py runserver
python start_celery.py
```

Скрипт предложит варианты: Worker+Beat, только Worker или только Beat.
Этот способ удобен для разработки и отладки (в нём worker и beat запускаются в процессе пользователя).

---

2) Запуск в Docker / продакшн

Рекомендуется запускать worker и beat как отдельные сервисы (или контейнеры):

Пример docker-compose (фрагмент):

```yaml
services:
  redis:
    image: redis:alpine
  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    depends_on:
      - redis
  celery-worker:
    build: .
    command: celery -A config worker --loglevel=info --concurrency=4
    depends_on:
      - redis
  celery-beat:
    build: .
    command: celery -A config beat --loglevel=info
    depends_on:
      - redis
```

В продакшне: используйте process manager (systemd / supervisor) или оркестрацию (k8s). 
Не запускайте worker и beat из-под учётной записи root в продакшене.

---

3) Основные настройки

В config/settings.py заданы параметры Celery:
- CELERY_BROKER_URL — брокер (redis)
- CELERY_RESULT_BACKEND — django-db
- CELERY_BEAT_SCHEDULE — периодические задачи

Если хотите отключить celery при тестах — в config/test_settings.py уже включены CELERY_ALWAYS_EAGER = True.

---

4) Полезные команды

Локально (при установленном celery):

```bash
# Запустить worker
celery -A config worker --loglevel=info

# Запустить beat
celery -A config beat --loglevel=info

# Проверить статус
celery -A config status

# Просмотреть зарегистрированные задачи
celery -A config inspect registered

# Запустить Flower (мониторинг)
pip install flower
celery -A config flower
# Откройте http://localhost:5555
```

---

5) Отладка и устранение неполадок

- Если задачи не выполняются: проверьте, что Redis доступен и CELERY_BROKER_URL корректен.
- Для подробной отладки запустите worker с --loglevel=debug.
- Если периодические задачи не выполняются — убедитесь, что celery-beat запущен и настройки CELERY_BEAT_SCHEDULE корректны.

---

6) Рекомендации по безопасности

- Не храните секреты (SECRET_KEY, ключи брокера) в коде — используйте переменные окружения / секреты CI.
- Настройте аутентификацию/пароль для Redis в продакшне и ограничьте сеть.
- Не запускайте Celery worker с ROOT-пользователем; используйте сервисного пользователя.

---

7) Дополнительно

- В проекте задачи объявлены в utils/celery_tasks.py — там же реализован TaskWrapper, который позволяет запускать задачи синхронно в тестах, если Celery недоступен.
- Для тестов Celery настроен в config/test_settings.py (CELERY_ALWAYS_EAGER=True).

---

← [Назад: README](README.md) | [← В README](README.md) | **Далее:** [PAYMENTS_SUMMARY.md](PAYMENTS_SUMMARY.md) → | [Все руководства](README.md#6-документы-и-подробные-руководства)
