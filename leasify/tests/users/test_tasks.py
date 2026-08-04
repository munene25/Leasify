from django.core.mail import EmailMessage

from leasify.authentication import tasks
from leasify.users.models import User
from leasify.users import tasks

from leasify.common.emails import email_context

class TestSendWelcomeEmailTask:

    def test_send_welcome_email(self, user: User, mailoutbox: list[EmailMessage]):
        """Verify welcome email is sent with correct subject, recipient, verify and unsubscribe urls."""
        tasks.send_welcome_email(
            user_id=user.pk,
            unsubscribe_url="unsubscribe",
            email_verify_url="verify-email",
        )

        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.subject == f"Welcome to {email_context.app_name}"
        assert mail.to == [user.email]
        assert "verify-email" in mail.body
        assert "unsubscribe" in mail.body
        assert user.get_full_name() in mail.body