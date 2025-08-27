# 🔄 Руководство по Celery в LearningPlatform

## Что такое Celery?

Celery - это система асинхронной обработки задач на Python. В нашем проекте используется для:

- ✉️ **Отправки email'ов** (уведомления, отчёты)
- 💳 **Обработки платежей** (проверка статусов, завершение)
- 🧹 **Очистки данных** (просроченные платежи, скидки)
- 📊 **Генерации отчётов** (статистика, аналитика)
- ⏰ **Периодических задач** (напоминания, бэкапы)

## 🚀 Быстрый запуск

### Установка зависимостей
```bash
pip install celery redis
```

### Запуск Redis (брокер сообщений)
```
# Windows
redis-server

# Linux/Mac
sudo systemctl start redis
```

### Запуск Celery
```
# Простой способ - используйте готовый скрипт
python start_celery.py

# Или запустите вручную
# Worker (обрабатывает задачи)
celery -A config worker --loglevel=info

# Beat (планировщик задач)
celery -A config beat --loglevel=info
```

## 📋 Доступные задачи

### Периодические задачи

| Задача | Описание | Расписание |
|--------|----------|------------|
| `cleanup_expired_payments` | Помечает просроченные платежи как неудачные | Каждые 6 часов |
| `cleanup_expired_discounts` | Убирает истёкшие скидки | Каждый час |
| `generate_daily_reports` | Отправляет ежедневные отчёты админам | 9:00 каждый день |
| `update_user_progress_stats` | Обновляет статистику студентов | 2:00 каждую ночь |
| `send_course_reminders` | Напоминания о незавершённых курсах | Понедельник 10:00 |

### Задачи по требованию

| Задача | Описание | Использование |
|--------|----------|---------------|
| `send_admin_key_email` | Отправляет админ-ключ на email | Автоматически при создании |
| `process_payment_completion` | Завершает платеж с автоповтором | После webhook от платёжки |
| `send_payment_success_notification` | Уведомление об успешной оплате | После завершения платежа |
| `generate_payment_analytics` | Генерирует аналитику платежей | По требованию |

## 🛠️ Как использовать

### Запуск задачи из кода
```python
from utils.celery_tasks import generate_daily_reports

# Асинхронно
result = generate_daily_reports.delay()

# Синхронно (для отладки)
result = generate_daily_reports()
```

### Запуск задачи из Django shell
```python
python manage.py shell

>>> from utils.celery_tasks import cleanup_expired_payments
>>> result = cleanup_expired_payments.delay()
>>> print(result.get())  # Получить результат
```

### Запуск задачи из админки
Можно создать admin actions для запуска задач:

```python
# В admin.py
@admin.action(description='Очистить просроченные платежи')
def cleanup_payments(modeladmin, request, queryset):
    from utils.celery_tasks import cleanup_expired_payments
    result = cleanup_expired_payments.delay()
    messages.success(request, f'Задача запущена: {result.id}')
```

## 🔧 Настройка

### Основные настройки (config/settings.py)
```python
# Брокер сообщений
CELERY_BROKER_URL = "redis://localhost:6379/1"

# Где хранить результаты
CELERY_RESULT_BACKEND = "django-db"

# Формат сообщений
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Часовой пояс
CELERY_TIMEZONE = "Europe/Moscow"
```

### Расписание задач
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'daily-cleanup': {
        'task': 'utils.celery_tasks.cleanup_expired_payments',
        'schedule': crontab(hour=2, minute=0),  # 2:00 каждый день
    },
}
```

## 📊 Мониторинг

### Flower - веб-интерфейс для Celery
```bash
pip install flower
celery -A config flower
```
Откройте http://localhost:5555 для мониторинга.

### Проверка статуса
```bash
# Список активных задач
celery -A config inspect active

# Статистика
celery -A config inspect stats

# Зарегистрированные задачи
celery -A config inspect registered
```

### Логи
```python
# В settings.py добавьте логирование
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'celery.log',
        },
    },
    'loggers': {
        'celery': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🚨 Устранение неполадок

### Redis не запускается
```bash
# Проверить статус
redis-cli ping

# Если отвечает PONG - всё работает

# Windows - установить Redis через Chocolatey
choco install redis-64
```

### Задачи не выполняются
1. Убедитесь, что Redis запущен
2. Проверьте, что worker запущен
3. Посмотрите логи: `celery -A config worker --loglevel=debug`

### Периодические задачи не работают
1. Убедитесь, что beat запущен
2. Проверьте расписание в настройках
3. Посмотрите логи beat'а

## 🎯 Полезные команды

```bash
# Запуск worker в фоне (Linux/Mac)
celery -A config worker --detach --loglevel=info

# Остановка всех worker'ов
celery -A config control shutdown

# Перезапуск worker'ов
celery -A config control restart

# Очистка всех задач
celery -A config purge

# Список задач в очереди
celery -A config inspect active
```

## 📈 Расширенные возможности

### Создание новой задачи
```python
# В apps/tasks.py
from celery import shared_task

@shared_task
def my_custom_task(param1, param2):
    # Ваш код здесь
    return "Результат выполнения"

# Использование
from apps.tasks import my_custom_task
result = my_custom_task.delay("значение1", "значение2")
```

### Задачи с автоповтором
```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def reliable_task(self, data):
    try:
        # Ваш код
        return "Success"
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

### Цепочки задач
```python
from celery import chain

# Последовательное выполнение
job = chain(
    task1.s(arg1),
    task2.s(),  # Получит результат task1
    task3.s(arg3)
)
result = job.apply_async()
```

## 🔐 Безопасность

1. **Не передавайте конфиденциальные данные** в параметрах задач
2. **Используйте результаты задач** для получения чувствительной информации
3. **Настройте аутентификацию** для Redis в продакшене
4. **Ограничивайте доступ** к портам Redis и Celery

## 🚀 Продакшен

### Docker Compose пример
```yaml
version: '3.8'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  celery-worker:
    build: .
    command: celery -A config worker --loglevel=info
    depends_on:
      - redis
  
  celery-beat:
    build: .
    command: celery -A config beat --loglevel=info
    depends_on:
      - redis
```

### Supervisor конфигурация (Linux)
```ini
[program:celery]
command=/path/to/venv/bin/celery -A config worker --loglevel=info
directory=/path/to/project
user=celery
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log
```

Готово! 🎉 Теперь у вас есть мощная система фоновых задач для LearningPlatform.