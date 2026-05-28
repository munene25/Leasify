import os

from celery import Celery
from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')


app.config_from_object('django.conf:settings', namespace='CELERY')


app.autodiscover_tasks()


app.conf.beat_schedule = {
    "terminate_reserved": {
        "task": "tenancy.tasks.reserved_set_terminated",
        'schedule': crontab(minute="*"),  # Every day at 1:00 AM
    },
    "month_start_tasks": {
        "task": "tenancy.tasks.month_start_tasks",
        "schedule": crontab(hour=0, minute=0, day_of_month=1),  # 1st of month at 12:00 AM
    },
}