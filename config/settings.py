from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

# загрузка переменных окружения из файла .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = True if os.getenv("DEBUG") == "True" else False

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_filters",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "Users",
    "Lessons",
    "Disciplines",
    "Teachers",
    "Admin",
    "Students",
    "Tests",
    "Payments",
    "utils",
    "celery",
    "django_celery_results",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        # "rest_framework.permissions.AllowAny", # Разрешить всем
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# настройки для JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=180),  # Время жизни access токена
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),  # Время жизни refresh токена
    "ROTATE_REFRESH_TOKENS": True,  # Автоматически обновлять refresh токен
    "BLACKLIST_AFTER_ROTATION": True,  # Черный список старых refresh токенов
    "UPDATE_LAST_LOGIN": True,  # Обновлять last_login при использовании токена
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    # Используйте SECRET_KEY из env или дефолтное значение
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "email",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=30),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
    "TOKEN_OBTAIN_SERIALIZER": "Users.serializers.CustomTokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
}

SPECTACULAR_SETTINGS = {
    "SWAGGER_UI_SETTINGS": {
        "DOC_EXPANSION": "none",
        "DEFAULT_MODEL_RENDERING": "example",
        "DEEP_LINKING": True,
    },
    "SERVE_INCLUDE_SCHEMA": False,  # Не включать схему в UI, если она уже доступна отдельно
    "SCHEMA_PATH_PREFIX": r"/api/",  # Префикс для всех путей в схеме
    "AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "PERMISSIONS_CLASSES": [
        "rest_framework.permissions.AllowAny",  # Разрешаем доступ к Swagger UI без аутентификации
    ],
    "TAGS": [
        {"name": "Информация. Читай и тыкай правильно."},
    ],
}

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "ru-ru"

TIME_ZONE = "Europe/Moscow"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")  # Папка, куда будут загружаться файлы

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Настройки кэширования с Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "1")  # Номер базы данных Redis

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "SERIALIZER": "django_redis.serializers.pickle.PickleSerializer",
            "PARSER_CLASS": "redis.connection.DefaultParser",
        },
        "KEY_PREFIX": "learningplatform_cache",
        "TIMEOUT": 300,
    }
}

# Используем Redis для кеширования сессий
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Настройки для загрузки фикстур
FIXTURE_DIRS = [
    os.path.join(BASE_DIR, "fixtures"),
]

# Email settings
# Настройки Email для тестирования и отладки, если что можно закомимтить, когда настроишь в .env
# для вывода писем в консоль вместо реальной отправки
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = ""
EMAIL_PORT = 587
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False

if EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = os.getenv("EMAIL_PORT")
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS") == "True"
    EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL") == "True"

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = "noreply@example.com"

AUTH_USER_MODEL = "Users.User"

LOGIN_URL = "/users/login/"
# Конфигурация Celery
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
CELERY_RESULT_BACKEND = (
    "django-db"  # Используем Django ORM для хранения результатов задач
)
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_OPTIMIZE_DIRECT = False
CELERY_WORKER_OPTIMIZATIONS = False
CELERY_WORKER_POOL = 'solo'
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Очистка просроченных платежей каждые 6 часов
    'cleanup-expired-payments': {
        'task': 'utils.celery_tasks.cleanup_expired_payments',
        'schedule': crontab(minute=0, hour='*/6'),
    },

    # Убираем истёкшие скидки каждый час
    'cleanup-expired-discounts': {
        'task': 'utils.celery_tasks.cleanup_expired_discounts',
        'schedule': crontab(minute=0),
    },

    # Ежедневный отчёт в 9:00
    'daily-reports': {
        'task': 'utils.celery_tasks.generate_daily_reports',
        'schedule': crontab(hour=9, minute=0),
    },

    # Обновление статистики пользователей каждую ночь в 2:00
    'update-user-stats': {
        'task': 'utils.celery_tasks.update_user_progress_stats',
        'schedule': crontab(hour=2, minute=0),
    },

    # Напоминания о курсах каждый понедельник в 10:00
    'send-course-reminders': {
        'task': 'utils.celery_tasks.send_course_reminders',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),
    },
}

# Настройки Stripe (намного проще!)
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_TEST_MODE = os.getenv("STRIPE_TEST_MODE", "True") == "True"

# URL для обработки webhook от Stripe
STRIPE_WEBHOOK_URL = f"{BASE_URL}/api/payments/stripe-webhook/"

# Настройки ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")
YOOKASSA_TEST_MODE = os.getenv("YOOKASSA_TEST_MODE", "True") == "True"

# URL для обработки webhook от ЮKassa
YOOKASSA_WEBHOOK_URL = f"{BASE_URL}/api/payments/yookassa-webhook/"
# для логгирования ошибок.
# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "handlers": {
#         "console": {
#             "class": "logging.StreamHandler",
#         },
#     },
#     "root": {
#         "handlers": ["console"],
#         "level": "DEBUG",
#     },
#     "loggers": {
#         "django": {
#             "handlers": ["console"],
#             "level": "DEBUG",
#             "propagate": False,
#         },
#         "django.db.backends": {
#             "handlers": ["console"],
#             "level": "DEBUG",
#             "propagate": False,
#         },
#     },
# }