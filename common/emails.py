from dataclasses import dataclass, asdict, fields
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from typing import Any

@dataclass(frozen=True)
class EmailConfig:
    frontend_domain: str = settings.FRONTEND_DOMAIN
    frontend_url: str = settings.FRONTEND_URL
    app_name: str = settings.APP_NAME
    company_name: str = settings.COMPANY_NAME
    company_address: str = settings.COMPANY_ADDRESS
    support_email: str = f"support@{settings.FRONTEND_DOMAIN}"
    default_from_email: str = "noreply@{settings.FRONTEND_DOMAIN}"
    
    @property
    def as_dict(self) -> dict[str, str]:
        return asdict(self)


email_context: EmailConfig = EmailConfig()


def send_template_email(
    *,
    to: list[str],
    subject: str,
    context: dict,
    template_name: str,
    from_email: str | None = None,
    attachment: Any | None = None,
    attachment_name: str = "attachment",
    attachment_type: str | None = None,
) -> None:
    """Inject additional context to the email renders and send the email"""

    context = {**context, **email_context.as_dict}
    text_content = render_to_string(f"emails/{template_name}.txt", context)
    html_content = render_to_string(f"emails/{template_name}.html", context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email or email_context.default_from_email,
        to=to,
    )
    if link := context.get("unsubscribe_url"):
        email.extra_headers = {
            "List-Unsubscribe": f"<{link}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
    if attachment:
        email.attach(attachment_name, attachment, attachment_type)

    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)