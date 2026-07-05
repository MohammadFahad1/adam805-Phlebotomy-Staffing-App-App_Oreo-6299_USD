import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'phlebotomy_staffing.settings')

app = Celery('phlebotomy_staffing')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()