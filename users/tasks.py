from celery import shared_task, Task
from .selectors import user_get_by_id
from config.emails import get_default_params, send_template_email
from .tokens import token_url_generate, unsubscribe_url_for
import smtplib



@shared_task(autoretry_for=(smtplib.SMTPDataError,),retry_kwargs={'max_retries': 3}, retry_backoff=True, retry_jitter=True)
def send_welcome_email(user_id: int):
    user = user_get_by_id(user_id)
    context = get_default_params()
    subject = f"Welcome to {context['app_name']}"
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
    user = user_get_by_id(user_id)
    context = get_default_params()
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

send_welcome_email: Task 
send_token_email: Task


