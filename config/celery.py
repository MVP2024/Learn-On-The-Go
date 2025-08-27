import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('LearningPlatform')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Явно указываем модули, в которых находятся задачи
app.autodiscover_tasks(['utils.celery_tasks', 'Users.tasks'])
