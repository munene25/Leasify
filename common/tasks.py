from typing import Callable
import smtplib
from celery import Task, shared_task


# A common task decorator for async email sending tasks
email_task: Callable[..., Task] = shared_task(autoretry_for=(smtplib.SMTPDataError, ConnectionError), retry_kwargs={'max_retries': 3}, retry_backoff=True, retry_jitter=True)

# A common task decorator for regular async tasks
regular_task: Callable[..., Task] = shared_task(retry_kwargs={"max_retries": 3}, retry_backoff=True)