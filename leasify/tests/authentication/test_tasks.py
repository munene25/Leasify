from django.core.mail import EmailMessage

from leasify.authentication import tasks
from leasify.users.models import User


class TestSendEmailTokenTask:

    def test_send_token_email(self, user: User, mailoutbox: list[EmailMessage]):
        """Verify token email is sent with correct subject, recipient and token url."""
        tasks.send_token_email(
            user_id=user.pk,
            url_path="reset-password",
            subject="Reset your password",
            action_cta="Reset Password",
        )

        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.subject == "Reset your password"
        assert mail.to == [user.email]
        assert "reset-password" in mail.body
        assert user.full_name in mail.body

class TestNotifyPasswordChangeTask:

    def test_notify_password_change(self, user: User, mailoutbox: list[EmailMessage]):
        """Verify password change email is sent with correct subject, recipient and token url."""
        tasks.notify_password_change(
            user_id=user.pk,
            url_path="recover-account",
        )

        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.subject == "Account password has been changed"
        assert mail.to == [user.email]
        assert "recover-account" in mail.body
        assert user.full_name in mail.body