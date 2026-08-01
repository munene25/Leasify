from leasify.common.emails import send_template_email, email_context

from leasify.users.selectors import user_get
from leasify.common.tasks import email_task
from leasify.authentication.tokens import build_user_url

@email_task
def send_welcome_email(user_id: int, unsubscribe_url: str, email_verify_url: str):
    user = user_get(user_id)
    context = {
        "verify_url": build_user_url(user=user, path=email_verify_url),
        "unsubscribe_url": build_user_url(user=user, path=unsubscribe_url, with_token=False)
    }
    subject = f"Welcome to {email_context.app_name}"
    send_template_email(
        subject=subject,
        context=context,
        to=[user.email],
        template_name="users/welcome"
    )
    return True


