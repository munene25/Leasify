import pytest
from datetime import timedelta

from unittest.mock import MagicMock


from django.utils import timezone
from django.urls import reverse
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.contrib.sessions.backends.db import SessionStore
from rest_framework import status

from leasify.authentication.tokens import token_generate, uidb64_generate

from leasify.users.models import User
from leasify.tests.helpers import parse_error, parse_message, check_links_in_mail
from leasify.tests.types import IsClient


class TestUserLoginView:
    path = reverse("authentication:login")

    def test_user_login_successful(self, user: User, client: IsClient, password: str):
        """User should be able to log in and a session should be created and last_login should be updated."""
        credentials = {"email": user.email, "password": password}

        response = client.post(self.path, credentials)
        data = parse_message(response)

        assert data["message"] == "Login successful"

        user.refresh_from_db()  # type: ignore
        assert user.last_login is not None
        assert (timezone.now() - user.last_login) <= timedelta(seconds=1)

        session_id = response.cookies["sessionid"].value
        assert SessionStore().exists(session_id)

    def test_csrf_required(self, user: User, csrf_client: IsClient, password: str):
        """Login should require a valid CSRF token."""
        credentials = {"email": user.email, "password": password}

        # No CSRF token
        response = csrf_client.post(self.path, credentials)
        error = parse_error(response, 403)[0]
        assert "CSRF Failed" in error["detail"]

    def test_throttling(self, user: User, client: IsClient, password: str, override_throttles):
        """Email scoped throttling should throttle based on email addresses"""
        bad_credentials = {"email": user.email, "password": "password"}

        # First wrong attempt should raise 401 for bad request
        response1 = client.post(self.path, bad_credentials)
        error1 = parse_error(response1, status.HTTP_401_UNAUTHORIZED, err_len=2)
        assert error1[0]["code"] == "authentication_failed"

        response2 = client.post(self.path, bad_credentials)
        error2 = parse_error(response2, status.HTTP_429_TOO_MANY_REQUESTS)[0]
        assert error2["code"] == "throttled"


class TestLogoutView:
    path = reverse("authentication:logout")

    def test_user_logut_successful(self, manager_client: IsClient):
        """Session should not exist, subsequent post should be unauthorized"""
        session_id = manager_client.cookies["sessionid"].value

        response2 = manager_client.post(self.path, {})
        data2 = parse_message(response2)
        assert "Logout" in data2["message"]
        assert not SessionStore().exists(session_id)

    def test_authentication(self, client: IsClient):
        res1 = client.post(self.path, {})
        error = parse_error(res1, status.HTTP_401_UNAUTHORIZED)[0]
        assert error["code"] == "not_authenticated"


class TestRefreshSessionView:
    path = reverse("authentication:refresh")

    def test_session_refresh_successful(self, user_client: IsClient):
        """
        There should exist a new expiry on the cookie expiring later than the first
        """
        session_id = user_client.cookies["sessionid"].value
        expiry1 = SessionStore(session_id).get_expiry_date()

        # -- Refresh the token and then compare expiry dates
        parse_message(user_client.post(self.path, {}))
        expiry2 = SessionStore(session_id).get_expiry_date()

        assert expiry1 < expiry2

    def test_authentication(self, client: IsClient):
        res1 = client.post(self.path, {})
        parse_error(res1, status.HTTP_401_UNAUTHORIZED)


class TestPasswordChangeView:
    path = reverse("authentication:password_change")
    payload = {
        "password": "Pa55word!",
        "new_password": "Pa22word!",
        "url_path": "password/reset",
    }

    @pytest.mark.parametrize("_client,code", [("user_client", status.HTTP_200_OK), ("client", status.HTTP_401_UNAUTHORIZED)])
    def test_authentication(self, request: pytest.FixtureRequest, _client: str, code: int):
        """Should raises 401 for unauthenticated"""
        client = request.getfixturevalue(_client)
        response = client.post(self.path, self.payload)
        assert response.status_code == code

    def test_password_changes_successfully(self, user_client: IsClient, mailoutbox: list[EmailMessage]):
        """Password should be changed successfully."""
        res = user_client.post(self.path, self.payload)
        data = parse_message(res)
        assert "Password" in data["message"]

        user = user_client.user
        user.refresh_from_db()  # type: ignore
        assert not user.check_password(self.payload["password"])
        assert user.check_password(self.payload["new_password"])

        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [user.email]
        assert self.payload["url_path"] in mail.body

    def test_session_cycled(self, monkeypatch: pytest.MonkeyPatch, user_client: IsClient):
        """updates session hash should be called"""
        from rest_framework.request import Request

        mock = MagicMock()
        monkeypatch.setattr("django.contrib.auth.update_session_auth_hash", mock)
        user_client.post(self.path, self.payload)
        args = mock.call_args.args
        assert isinstance(args[0], Request)
        assert args[1] == user_client.user

    @pytest.mark.parametrize("wrong_pass", ["wrongpassword", ""])
    def test_wrong_passwords_fail(self, wrong_pass: str, user_client: IsClient):
        """
        Incorrect or empty current password should fail.
        """
        payload = {**self.payload, "password": wrong_pass}
        res = user_client.post(self.path, payload)
        parse_error(res, status.HTTP_400_BAD_REQUEST, err_type="validation_error")

    def test_password_change_throttles(self, user_client: IsClient, override_throttles, cache_clear):
        """Requests should be throttled after exceeding the limit."""
        wrong_credentials = {**self.payload, "password": "Password"}

        response1 = user_client.post(self.path, wrong_credentials)
        parse_error(response1, status.HTTP_400_BAD_REQUEST, "validation_error")

        response2 = user_client.post(self.path, wrong_credentials)
        parse_error(response2, status.HTTP_429_TOO_MANY_REQUESTS)

        # New implementation does not pop last cache entry
        cache.clear()

        response3 = user_client.post(self.path, self.payload)
        parse_message(response3)

        response4 = user_client.post(self.path, self.payload)
        parse_error(response4, status.HTTP_429_TOO_MANY_REQUESTS)

    @pytest.mark.parametrize("_client,code", [("user_client", status.HTTP_200_OK), ("client", status.HTTP_401_UNAUTHORIZED)])
    def test_password_change_requires_authentication(self, _client: str, request: pytest.FixtureRequest, code: int):
        """Unauthenticated users should not be able to change passwords."""
        client = request.getfixturevalue(_client)
        response = client.post(self.path, self.payload)
        assert response.status_code == code


class TestRequestPasswordResetView:
    path = reverse("authentication:send_password_reset")

    def test_password_reset_successful(self, user: User, client: IsClient, mailoutbox: list[EmailMessage], cache_clear):
        """Unauthenticated users allowed. Email sent"""

        res1 = client.post(self.path, {"email": user.email, "url_path": "path/to/action"})
        parse_message(res1, status.HTTP_202_ACCEPTED)
        mail = mailoutbox[0]
        assert mail.to == [user.email]
        check_links_in_mail(user=user, mail=mail, path="path/to/action", with_token=True, with_uidb64=True)

    def test_throttles_based_on_email(self, client: IsClient, user_client: IsClient, override_throttles, cache_clear):
        """Should throttle based on the email address provided in the request body."""

        payload = {"email": "email@example.com", "url_path": "path/to/action"}
        res1 = client.post(self.path, payload)
        parse_message(res1, status.HTTP_202_ACCEPTED)

        res2 = user_client.post(self.path, payload)
        errs2 = parse_error(res2, status.HTTP_429_TOO_MANY_REQUESTS)
        assert errs2[0]["code"] == "throttled"

    def test_serializer(self, client: IsClient):
        """Wrong email formats should raise an error"""
        res1 = client.post(self.path, {"email": "email.com", "url_path": "path/to/action"})
        parse_error(res1, status.HTTP_400_BAD_REQUEST, "validation_error")

    def test_uniform_status_codes_even_for_unknown_emails(self, client: IsClient, mailoutbox: list[EmailMessage]):
        """
        Should fail on unregistered email but return uniform response
        """
        res1 = client.post(self.path, {"email": "test@email.com", "url_path": "path/to/action"})
        parse_message(res1, status.HTTP_202_ACCEPTED)
        assert len(mailoutbox) == 0


class TestConfirmPasswordResetView:
    def path(self, *args: str) -> str:
        return reverse("authentication:confirm_password_reset", args=args)

    payload = {"new_password": "NewPa55word!", "url_path": "path/to/action"}

    def test_password_reset(self, user_client: IsClient, client):
        """Unauthenticated clients should be allowed to post"""

        user = user_client.user
        # We need to refetch the user with updated logins
        user.refresh_from_db()  # type: ignore

        path = self.path(uidb64_generate(user), token_generate(user))

        res2 = client.post(path, self.payload)
        parse_message(res2)

        user.refresh_from_db()  # type: ignore
        user.verify_password(self.payload["new_password"])

        # Oringinal user_client should be logged out
        res3 = user_client.get("/users/me")
        parse_error(res3, status.HTTP_401_UNAUTHORIZED)

    def test_mail_links(self, user_client: IsClient, mailoutbox: list[EmailMessage]):
        user = user_client.user
        user.refresh_from_db()  # type: ignore

        path = self.path(uidb64_generate(user), token_generate(user))
        user_client.post(path, self.payload)
        assert len(mailoutbox) == 1
        user.refresh_from_db()  # type: ignore

        check_links_in_mail(
            mail=mailoutbox[0], 
            path=self.payload["url_path"], 
            with_uidb64=True, 
            with_token=True,
            user=user,
        )


class TestRequestEmailVerificationView:
    path = reverse("authentication:send_email_verification")

    def test_request_email_verification_successfull(self, user_client: IsClient, mailoutbox: list[EmailMessage]):
        """Should send correct email with correct link"""
        payload = {"url_path": "password-reset/confirm"}

        res1 = user_client.post(self.path, payload)
        parse_message(res1, status.HTTP_202_ACCEPTED)
        assert len(mailoutbox) == 1

        mail = mailoutbox[0]
        user = user_client.user
        assert mail.to == [user.email]
        check_links_in_mail(user=user, mail=mail, path=payload["url_path"])

    def test_reqest_does_not_send_email_for_verified_user(self, user_client: IsClient, mailoutbox: list[EmailMessage]):
        """
        message response will always be 202 but email will not be sent
        """
        User.objects.filter(pk=1).update(verified=True)

        res1 = user_client.post(self.path, {"url_path": "path/to/action"})
        parse_message(res1, status.HTTP_202_ACCEPTED)
        assert len(mailoutbox) == 0

    def test_authentication(self, client: IsClient):
        res1 = client.post(self.path, {})
        parse_error(res1, status.HTTP_401_UNAUTHORIZED)


class TestConfirmEmailVerificationView:
    def path(self, *args):
        return reverse("authentication:confirm_email_verification", args=args)

    def test_confirm_email_verification_successful(self, user: User, client: IsClient):
        """Should work with unauthenticated client. Url parsing should succeed"""

        from leasify.authentication.tokens import uidb64_generate, token_generate

        path = self.path(uidb64_generate(user), token_generate(user))
        res = client.post(path, {})
        parse_message(res)
        user.refresh_from_db()  # type: ignore
        assert user.verified == True

    def test_with_invalid_link(self, client: IsClient):
        """Invalid link should raise link malformed"""

        response = client.post(self.path("user", "invalid-token"), {"url_path": "path/to/action"})
        errors = parse_error(response, status.HTTP_400_BAD_REQUEST)
        assert errors[0]["code"] == "link_malformed"


class TestGetCSRFView:
    path = reverse("authentication:csrf")

    def test_csrf_set(self, client: IsClient):
        """Should allow unauthenticated clients as well as set cookie after request"""
        response = client.get(self.path, {})
        assert response.data["message"] == "csrf set"
        assert response.cookies["csrftoken"] is not None
