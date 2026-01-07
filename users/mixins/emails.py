from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

class EmailSenderMixin:
    def _send_template_email(
        self,
        *,
        subject: str,
        template_html: str,
        template_txt: str,
        context: dict,
        to_email: str,
        from_email: str | None = None,
    ):
        from_email = from_email or settings.EMAIL_HOST_USER
        extras = {
            "app_name": settings.APP_NAME,
            "support_email": settings.SUPPORT_EMAIL,
            "company_name": "Bisika Apartments",
            "company_address": "Embu, Kenya",
        }
        context.update(extras)
        text_content = render_to_string(template_txt, context)
        html_content = render_to_string(template_html, context)

        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.extra_headers = {"List-Unsubscribe": f"<mailto:{settings.SUPPORT_EMAIL}>"}
        msg.send(fail_silently=False)
