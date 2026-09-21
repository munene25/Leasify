from leasify.common.emails import send_template_email
from leasify.common.tasks import email_task

@email_task
def contact_service(
    email: str,
    full_name: str,
    message: str,
    reply_url: str,
    additional_recepients: list[str],
    phone_number: str | None = None,
) -> None:
    """
    Send details to admins and send acknowledgement email.
    """
    send_template_email(
        to=[email],
        subject="We got your message.",
        context={"full_name": full_name},
        template_name="contact/email_contact_ack"
    )
    send_template_email(
        to=additional_recepients,
        subject="We got your message.",
        context={
            "full_name": full_name,
            "email": email,
            "message": message,
            "phone_number": phone_number,
            "reply_url": reply_url
        },
        template_name="contact/email_contact_admin"
    )

@email_task
def reply_to_email(email: str, full_name: str, reply_message: str, original_message: str | None = None):
    """Reply to messages via email"""
    from leasify.common.emails import email_context

    send_template_email(
        to=[email],
        subject=f"Message from {email_context.app_name}",
        context={
            "full_name": full_name,
            "reply_message": reply_message,
            "original_message": original_message,
        },
        template_name="contact/send_message"
    )