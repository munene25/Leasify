from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def get_default_params() -> dict[str, str]:
    attrs = [
        "site_domain",
        "site_url",
        "app_name",
        "support_email",
        "default_from_email",
    ]
    params = {}
    for a in attrs:
        params[a] = getattr(settings, a.upper())
    params["company_name"] = params["app_name"]
    params["company_address"] = "Embu, Kenya"
    return params


def send_template_email(
    *,
    to: list[str],
    subject: str,
    context: dict,
    template_name: str,
    from_email: str | None = None,
) -> None:
    text_content = render_to_string(f"{template_name}.txt", context)
    html_content = render_to_string(f"{template_name}.html", context)
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email or context["default_from_email"],
        to=to,
    )
    if link := context.get("unsubscribe_url"):
        email.extra_headers = {
            "List-Unsubscribe": f"<{link}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }

    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)
