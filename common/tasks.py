import smtplib
from typing import Callable
from celery import Task, shared_task

type TaskDecorator = Callable[[Callable], Task]

class EmailTask(Task):
    """Base task for email operations."""
    autoretry_for = (smtplib.SMTPException, ConnectionError, TimeoutError)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_jitter = True
    time_limit = 120

class RegularTask(Task):
    """Base task for regular async operations."""
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_jitter = True

class CriticalTask(Task):
    """Base task for critical operations (payments, callbacks)."""
    autoretry_for = (Exception,)
    max_retries = 5
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    time_limit = 600
    soft_time_limit = 580


email_task: TaskDecorator = shared_task(base=EmailTask)
regular_task: TaskDecorator = shared_task(base=RegularTask)
critical_task: TaskDecorator = shared_task(base=CriticalTask)