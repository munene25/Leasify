from .selectors import user_get
from config.emails import send_template_email, email_context
from .tokens import token_url_generate, unsubscribe_url_for
import smtplib
from typing import Callable
from celery import shared_task, Task 


shared_task: Callable[..., Callable[[Callable], Task]]


@shared_task(autoretry_for=(smtplib.SMTPDataError,),retry_kwargs={'max_retries': 3}, retry_backoff=True, retry_jitter=True) 
def send_welcome_email(user_id: int):
    user = user_get(user_id)
    context = {
        "verify_url": token_url_generate(user=user, path="email-verify"),
        "unsubscribe_url": unsubscribe_url_for(user)
    }
    subject = f"Welcome to {email_context.app_name}"
    send_template_email(
        subject=subject,
        context=context,
        to=[user.email],
        template_name="emails/welcome"
    )
    return True

@shared_task(autoretry_for=(smtplib.SMTPDataError, ConnectionError), retry_kwargs={'max_retries': 3}, retry_backoff=True, retry_jitter=True)
def send_token_email(user_id: int, url_path: str, subject: str, action_cta: str):
    user = user_get(user_id)
    context = {
        "recipient_name": user.get_full_name(),
        "token_url":  token_url_generate(user=user, path=url_path),
        "action_cta": action_cta
    }
    send_template_email(
        subject=subject,
        context=context,
        to=[user.email],
        template_name="emails/token"
    )
    return True

@shared_task(autoretry_for=(smtplib.SMTPDataError, ConnectionError), retry_kwargs={'max_retries': 3}, retry_backoff=True, retry_jitter=True)
def notify_password_change(user_id: int):
    user = user_get(user_id)
    context = {
        "recipient_name": user.get_full_name(),
        "token_url":  token_url_generate(user=user, path="password-reset"),
    }
    subject = "Account password has been changed"
    send_template_email(
        subject=subject,
        context=context,
        to=[user.email],
        template_name="emails/password_changed"
    )


