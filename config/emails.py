from dataclasses import dataclass, asdict, fields
from functools import cached_property, lru_cache
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


@dataclass(frozen=True)
class EmailConfig:
    frontend_domain: str
    frontend_url: str
    app_name: str
    support_email: str
    default_from_email: str
    company_name: str
    company_address: str

    @classmethod
    def load(cls):
        values = {}
        for f in fields(cls):
            values[f.name] = getattr(settings, f.name.upper())
        return cls(**values)

    @cached_property
    def as_dict(self) -> dict[str, str]:
        return asdict(self)


email_context: EmailConfig = EmailConfig.load()


def send_template_email(
    *,
    to: list[str],
    subject: str,
    context: dict,
    template_name: str,
    from_email: str | None = None,
) -> None:
    """Inject additional context to the email renderes and send the email"""

    context = {**context, **email_context.as_dict}
    text_content = render_to_string(f"{template_name}.txt", context)
    html_content = render_to_string(f"{template_name}.html", context)

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

    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)
