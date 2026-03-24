import smtplib
from typing import Callable
from celery import shared_task, Task
from config.emails import send_template_email, email_context
from users.tokens import build_user_url
from users.selectors import user_get



auto_retry: Callable[..., Task] = shared_task(autoretry_for=(smtplib.SMTPDataError, ConnectionError), retry_kwargs={'max_retries': 3}, retry_backoff=True, retry_jitter=True)

@auto_retry
def send_welcome_email(user_id: int):
    user = user_get(user_id)
    context = {
        "verify_url": build_user_url(user=user, path="email-verify"),
        "unsubscribe_url": build_user_url(user=user, path="unsubscribe", with_token=False)
    }
    subject = f"Welcome to {email_context.app_name}"
    send_template_email(
        subject=subject,
        context=context,
        to=[user.email],
        template_name="emails/welcome"
    )
    return True

@auto_retry
def send_token_email(user_id: int, url_path: str, subject: str, action_cta: str):
    user = user_get(user_id)
    context = {
        "recipient_name": user.get_full_name(),
        "token_url":  build_user_url(user=user, path=url_path),
        "action_cta": action_cta
    }
    send_template_email(
        subject=subject,
        context=context,
        to=[user.email],
        template_name="emails/token"
    )
    return True

@auto_retry
def notify_password_change(user_id: int):
    user = user_get(user_id)
    context = {
        "recipient_name": user.get_full_name(),
        "token_url":  build_user_url(user=user, path="password-reset"),
    }
    subject = "Account password has been changed"
    send_template_email(
        subject=subject,
        context=context,
        to=[user.email],
        template_name="emails/password_changed"
    )


