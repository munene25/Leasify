import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
# Load task modules from all registered Django apps.
app.autodiscover_tasks()

CELERY_BEAT_SCHEDULE = {
    "terminate_reserved": {
        "task": "tenancy.tasks.terminate_reserved",
        'schedule': crontab(hour=1, minute=0),  # Every day at 1:00 AM
    },
    "month_start_tasks": {
        "task": "tenancy.tasks.month_start_tasks",
        "schedule": crontab(hour=0, minute=0, day_of_month=1),  # 1st of month at 12:00 AM
    },
}