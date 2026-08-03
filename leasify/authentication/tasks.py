from leasify.common.emails import send_template_email
from leasify.common.tasks import email_task
from leasify.authentication.tokens import build_user_url
from leasify.users.selectors import user_get

@email_task
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
        template_name="users/token"
    )
    return True

@email_task
def notify_password_change(user_id: int, url_path: str):
    user = user_get(user_id)
    context = {
        "recipient_name": user.get_full_name(),
        "token_url":  build_user_url(user=user, path=url_path),
    }
    subject = "Account password has been changed"
    send_template_email(
        subject=subject,
        context=context,
        to=[user.email],
        template_name="users/password_changed"
    )

