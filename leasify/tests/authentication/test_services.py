import pytest

from django.core.mail import EmailMessage
from rest_framework.exceptions import ValidationError, AuthenticationFailed

from leasify.authentication import services as s
from leasify.users.models import User


class TestUserEmailVerifyConfirmation:
    def test_email_set_as_verified(self, user: User):
        """
        Verified status should reflect
        """
        mod_user = s.user_email_verify(user)
        mod_user.refresh_from_db() # type: ignore
        assert mod_user == user
        assert mod_user.verified == True


class TestLoginService:
    def test_authenticate_service_succeeds(self, user: User, password: str):
        """
        credentials passed should correctly return an authenticated user
        last_login field should be updated
        returned user should be the match
        """
        authenticated_user = s.user_authenticate(email=user.email, password=password)
        assert authenticated_user == user

    def test_login_service_fails_with_inactive_users(self, user: User):
        user.is_active = False
        user.save(update_fields=["is_active"])

        with pytest.raises(AuthenticationFailed) as exc:
            s.user_authenticate(email=user.email, password="Pa55word!")
        assert "email" in exc.value.detail and "password" in exc.value.detail

    def test_login_fails_for_wrong_credentials(self, user: User):
        wrong_email = "test@testemail.com"
        wrong_pass = "password"
        with pytest.raises(AuthenticationFailed) as exc:
            s.user_authenticate(email=wrong_email, password=wrong_pass)
        assert "email" in exc.value.detail and "password" in exc.value.detail

    def test_login_succeds_with_normalization(self, user: User):
        """
        User lookups should use normalized emails
        """
        parts = user.email.split("@")
        email = parts[0] + "@" + parts[1].upper()
        authd_user = s.user_authenticate(email=email, password="Pa55word!")
        assert authd_user == user


class TestUserChangePassword:
    def test_password_change_successful(self, user: User) -> None:
        """
        A users password be hashed
        The new password should work pass check_password
        The old password should not work
        """
        current_password = "Pa55word!"
        new_password = "TimT@tman!"
        user.validate_password(current_password)
        modified = s.user_change_password(user=user, new_password=new_password, password=current_password)
        assert user == modified == User.objects.get(pk=user.pk)
        # Password should be hashed
        assert modified.password != new_password
        # Should not raise error
        modified.validate_password(new_password)
        # Should raise error
        with pytest.raises(ValidationError) as exc:
            modified.validate_password(current_password)
        assert "password" in exc.value.detail

    def test_password_change_sends_email(
        self,
        user: User,
        mailoutbox: list[EmailMessage],
        django_capture_on_commit_callbacks,
    ) -> None:
        """
        Check the mail is sent to the correct user
        contains the correct subject, links, and body
        """
        from leasify.common.emails import email_context

        current_password = "Pa55word!"
        new_password = "TimT@tman!"
        user.validate_password(current_password)
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            s.user_change_password(user=user, new_password=new_password, password=current_password)
        assert len(callbacks) == 1
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.subject == "Account password has been changed"
        assert mail.from_email == email_context.default_from_email
        assert mail.to == [user.email]
        assert "password-reset" in mail.body

    def test_password_changed_without_password(self, user: User):
        new_password = "Everl@sting!"
        mod_user = s.user_change_password(user=user, new_password=new_password, is_ressetting=True)
        assert mod_user == user
        mod_user.validate_password(new_password)