import pytest
from unittest.mock import MagicMock


from rest_framework.exceptions import ValidationError, AuthenticationFailed

from leasify.authentication import services as s
from leasify.users.models import User


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


class TestUserEmailVerifyConfirmation:
    def test_email_set_as_verified(
        self,
        user: User,
    ):
        """
        Verified status should reflect
        """
        mod_user = s.user_email_verify(user)
        mod_user.refresh_from_db()  # type: ignore
        assert mod_user == user
        assert mod_user.verified == True


class TestUserChangePassword:
    def test_case_for_changing_password(self, user: User, password: str, patch_notify_password_change: MagicMock) -> None:
        """
        A users password be hashed
        The new password should work pass check_password
        The old password should not work
        """
        new_password = "TimT@tman!"
        user.verify_password(password)
        modified = s.user_change_password(user=user, new_password=new_password, password=password, url_path="path/to/verify")
        assert user == modified == User.objects.get(pk=user.pk)
        # Password should be hashed
        assert modified.password != new_password
        # Should not raise error
        modified.verify_password(new_password)
        # Should raise error
        with pytest.raises(ValidationError) as exc:
            modified.verify_password(password)
        assert "password" in exc.value.detail

        patch_notify_password_change.assert_called_once_with(user.pk, "path/to/verify")

    def test_case_when_resetting_password(self, user: User, password: str, patch_notify_password_change: MagicMock):
        """In case of resetting, password is not required"""

        new_password = "NewPassword"
        modified = s.user_change_password(
            user=user, new_password=new_password, is_ressetting=True, url_path="some-path"
        )
        user.refresh_from_db() # type: ignore
        assert modified == user

        user.verify_password(new_password)

        with pytest.raises(ValidationError, match="password"):
            user.verify_password(password)

    def test_mail_sending_called_with_correct_args(self, user: User, patch_notify_password_change: MagicMock, password: str):
        """Patch delay and confirm called with correct args"""

        frontend_path = "path/to/frontend"

        s.user_change_password(user=user, new_password=password, password=password, url_path=frontend_path)
        patch_notify_password_change.assert_called_once_with(user.pk, frontend_path)
