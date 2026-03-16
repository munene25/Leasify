from .selectors import user_get
from config.emails import send_template_email, EmailConfig
from .tokens import token_url_generate, unsubscribe_url_for
import smtplib
from typing import Callable
from celery import shared_task, Task 


shared_task: Callable[..., Callable[[Callable], Task]]

config = EmailConfig.load()

@shared_task(autoretry_for=(smtplib.SMTPDataError,),retry_kwargs={'max_retries': 3}, retry_backoff=True, retry_jitter=True) 
def send_welcome_email(user_id: int):
    user = user_get(user_id)
    context = config.as_dict
    subject = f"Welcome to {config.app_name}"
    context["verify_url"] = token_url_generate(user=user, path="email-verify")
    context["unsubscribe_url"] = unsubscribe_url_for(user)
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
    context = EmailConfig.load().as_dict
    context["recipient_name"] = user.get_full_name()
    context["url"] = token_url_generate(user=user, path=url_path)
    context["action_cta"] = action_cta
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
    context = config.as_dict
    context["recipient_name"] = user.get_full_name()
    context["url"] = token_url_generate(user=user, path="password-reset")
    subject = "Account password has been changed"
    send_template_email(
        subject=subject,
        context=context,
        to=[user.email],
        template_name="emails/password_changed"
    )


