from .settings import *  # noqa: F401,F403

# Используем in-memory SQLite для тестов для скорости
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Отключаем миграции для тестов
MIGRATION_MODULES = {
    "auth": None,
    "contenttypes": None,
    "Users": None,
    "Disciplines": None,
    "Lessons": None,
    "Exercises": None,
    "Payments": None,
    "Teachers": None,
    "Students": None,
    "Admin": None,
}

# Ускоряем выполнение паролей (для тестов нет необходимости в сильном хешировании)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# Отключаем Celery для тестов
CELERY_ALWAYS_EAGER = True
CELERY_TASK_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
BROKER_BACKEND = "memory"

# Отключаем кэширование
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# Отключаем логирование (опционально, можно настроить по необходимости)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["null"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Для ускорения тестов, если не требуются реальные файлы
MEDIA_ROOT = None
STATIC_ROOT = None

# Отключаем почту
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
