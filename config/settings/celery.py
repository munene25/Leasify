import os

from celery import Celery
from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django.base')

app = Celery('config')


app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# It really is just better to have them run with utc time as most tasks require filtering based on dates.
# ! Midnight UTC => 3AM (UTC+3)
app.conf.beat_schedule = {
    "notify_reserved": {
        "task": "tenancy.tasks.notify_reserved_on_expiry",
        'schedule': crontab(hour=0, minute=0),  # Every day at 12:00 AM
    },
    "terminate_reserved": {
        "task": "tenancy.tasks.reserved_set_terminated",
        'schedule': crontab(hour=0, minute=0),  # Every day at 12:00 AM
    },
    "month_start_tasks": {
        "task": "tenancy.tasks.month_start_tasks",
        "schedule": crontab(hour=0, minute=0, day_of_month=1),  # 1st of month at 12:00 AM
    },
}