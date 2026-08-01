import pytest
from datetime import timedelta

from unittest.mock import patch, MagicMock
from freezegun import freeze_time

from django.utils import timezone
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.contrib.sessions.backends.db import SessionStore
from rest_framework import status

from leasify.users.models import User
from leasify.tests.helpers import parse_error, parse_message, check_links_in_mail

from leasify.tests.types import IsClient



class TestUserLoginView:
    path = "/auth/login"

    def test_user_login_successful(self, user: User, csrf_client: IsClient, password: str):
        """
        Csrf should be explicitly enforced even for unauthenticated users
        last login should be updated.
        A session should be created.
        """
        csrftoken = csrf_client.get("/csrf-token/").cookies["csrftoken"].value
        header = {"HTTP_X_CSRFTOKEN": csrftoken}
        credentials = {"email": user.email, "password": password}

        # -- With csrf tokens  --
        response1 = csrf_client.post(self.path, credentials, **header)
        data1 = parse_message(response1)
        assert data1["email"] == user.email
        user.refresh_from_db()  # type: ignore
        assert user.last_login is not None
        assert (user.last_login - timezone.now()) <= timedelta(seconds=1)

        session_id = response1.cookies["sessionid"].value
        session = SessionStore(session_key=session_id)
        session_data = session.load()

        assert len(session_data) > 1

        # -- Without csrf token --
        response2 = csrf_client.post(self.path, credentials)
        error = parse_error(response2, 403)[0]
        assert "CSRF Failed" in error["detail"]

        # -- WIth csrf token Wrong credentials --
        response3 = csrf_client.post(self.path, credentials, **header)
        parse_error(response3, 403)

    def test_throttling(self, user: User, client: IsClient, password: str, override_throttles, cache_clear):
        """
        Email scoped throttling should throttle based on email addresses not attempts
        """
        credentials = {"email": user.email, "password": password}
        bad_credentials = {"email": user.email, "password": "password"}

        # First attempt should be successful
        response1 = client.post(self.path, credentials)
        parse_message(response1)

        # A second time should qualify as a successfull login
        response2 = client.post(self.path, credentials)
        parse_message(response2)

        # First wrong attempt should raise 401 for bad request
        response3 = client.post(self.path, bad_credentials)
        error3 = parse_error(response3, status.HTTP_401_UNAUTHORIZED, err_len=2)
        assert error3[0]["code"] == "authentication_failed"

        response4 = client.post(self.path, bad_credentials)
        error4 = parse_error(response4, status.HTTP_429_TOO_MANY_REQUESTS)[0]
        assert error4["code"] == "throttled"


class TestLogoutView:
    path = "/auth/logout"

    def test_user_logut_successful(self, manager_user: User, client: IsClient, password: str):
        """
        Trying with manager client for variety
        Session should not exist
        Cookie should be unavailable
        Subsequent request should be denied
        """
        session = SessionStore()
        response1 = client.post("/users/login", {"email": manager_user.email, "password": password})
        session_id = response1.cookies["sessionid"].value
        assert session.exists(session_id) == True

        response2 = client.post(self.path, {})
        data2 = parse_message(response2)
        assert "logged out" in data2["message"]
        assert response2.cookies["sessionid"].value is ""
        assert session.exists(session_id) == False

        response3 = client.get("/users/")
        parse_error(response3, status.HTTP_401_UNAUTHORIZED)

    def test_authentication(self, client):
        res1 = client.post(self.path, {})
        error = parse_error(res1, status.HTTP_401_UNAUTHORIZED)[0]
        assert error["code"] == "not_authenticated"


class TestRefreshSessionView:
    path = "/auth/refresh"

    def test_user_can_refresh_their_session(self, user: User, user_client: IsClient, password: str):
        """
        There should exist a new expiry on the cookie expiring later than the first
        """
        # -- Login and check if token is issued --
        res1 = user_client.post("/users/login", {"email": user.email, "password": password})
        parse_message(res1)
        session_id = res1.cookies["sessionid"].value
        assert SessionStore().exists(session_id) == True
        expiry1 = SessionStore(session_id).get_expiry_date()

        # -- Refresh the token and then compare expiry dates
        res2 = user_client.post(self.path, {})
        parse_message(res2)
        expiry2 = SessionStore(session_id).get_expiry_date()

        assert expiry1 < expiry2

    def test_unauthenticated_requests_fails(self, client: IsClient):
        res1 = client.post(self.path, {})
        parse_error(res1, status.HTTP_401_UNAUTHORIZED)


class TestPasswordChangeView:
    path = "/auth/password-change"
    payload = {"password": "Pa55word!", "new_password": "Pa22word!", "confirm_password": "Pa22word!"}

    def test_password_change_successfull(
        self,
        superuser: User,
        superuser_client: IsClient,
        mailoutbox: list[EmailMessage],
        django_capture_on_commit_callbacks,
        override_throttles,
        cache_clear,
    ):
        """
        Password should be changed and message in response
        user should be able to login
        session_id should be cycled
        """

        session_id1 = (
            superuser_client.post("/users/login", {"email": superuser.email, "password": "Pa55word!"})
            .cookies["sessionid"]
            .value
        )
        old_password = superuser.password

        # -- with correct credentials should evaluate --
        with django_capture_on_commit_callbacks(execute=True):
            res1 = superuser_client.post(self.path, self.payload)
        session_id2 = res1.cookies["sessionid"].value
        data1 = parse_message(res1)
        assert "successfully updated" in data1["message"]
        superuser.refresh_from_db()  # type: ignore
        assert old_password != superuser.password
        assert not superuser.check_password(self.payload["password"])
        assert superuser.check_password(self.payload["new_password"])

        # -- sessionid should be cycled --
        store = SessionStore()
        assert store.exists(session_key=session_id1) == False
        assert store.exists(session_key=session_id2) == True

        # -- mail containing password reset link should be sent --
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [superuser.email]
        assert "password-reset" in mail.body

        # -- subsequent password changes should go through --
        password = self.payload["new_password"]
        res2 = superuser_client.post(self.path, {**self.payload, "password": password})
        parse_message(res2)

    @pytest.mark.parametrize("wrong_pass", ["wrongpassword", ""])
    def test_wrong_passwords_fail(self, user: User, wrong_pass: str, user_client: IsClient, cache_clear):
        """
        Wrong or empty("") passwords should fail
        """
        payload = {**self.payload, "password": wrong_pass}
        old_password = user.password
        # -- should raise 400 for invalid passwords --
        res1 = user_client.post(self.path, payload)
        error1 = parse_error(res1, status.HTTP_400_BAD_REQUEST, err_type="validation_error")[0]
        assert error1["attr"] == "password"
        user.refresh_from_db()  # type: ignore
        assert old_password == user.password

    def test_password_change_throttles(self, user_client: IsClient, override_throttles, cache_clear):
        """
        I'll test for non matching passwords here as well with the serializer
        Throttles should work after time elapses
        """
        before = timezone.now()
        fetch = lambda: user_client.post(self.path, {**self.payload, "new_password": "not password"})
        after = before + timedelta(hours=1)
        with freeze_time(before, tz_offset=0) as freeze:
            errors1 = parse_error(fetch(), status.HTTP_400_BAD_REQUEST, "validation_error")
            assert errors1[0]["attr"] == "confirm_password"
            errors2 = parse_error(
                fetch(),
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
            assert errors2[0]["code"] == "throttled"

            freeze.move_to(after)
            errors3 = parse_error(fetch(), status.HTTP_400_BAD_REQUEST, "validation_error")
            assert errors3[0]["attr"] == "confirm_password"

    def test_password_change_fails_for_unauthenticated(self, client: IsClient):
        """
        Raises 400 for unauthenticated
        """
        res1 = client.post(self.path, {**self.payload, "new_password": "not password"})
        errors = parse_error(res1, status.HTTP_401_UNAUTHORIZED)
        assert errors[0]["code"] == "not_authenticated"


class TestRequestEmailVerificationView:
    path = "/auth/email-verification/request"

    def test_request_email_verification_successfull(
        self, user: User, user_client: IsClient, django_capture_on_commit_callbacks, mailoutbox: list[EmailMessage]
    ):
        """
        mail should have a link to verify
        mail should be sent to the correct person
        """

        with django_capture_on_commit_callbacks(execute=True):
            res1 = user_client.post(self.path, {})
            parse_message(res1, status.HTTP_202_ACCEPTED)
        assert len(mailoutbox) == 1

        mail = mailoutbox[0]
        assert mail.to == [user.email]
        check_links_in_mail(user=user, mail=mail, path="email-verify")

    def test_reqest_does_not_send_email_for_verified_user(
        self, user: User, user_client: IsClient, django_capture_on_commit_callbacks, mailoutbox: list[EmailMessage]
    ):
        """
        message response will always be 202 but email will not be sent
        """
        user.verified = True
        user.save(update_fields=["verified"])

        with django_capture_on_commit_callbacks(execute=True):
            res1 = user_client.post(self.path, {})
            parse_message(res1, status.HTTP_202_ACCEPTED)
        assert len(mailoutbox) == 0

    def test_authentication(self, client: IsClient):
        res1 = client.post(self.path, {})
        parse_error(res1, status.HTTP_401_UNAUTHORIZED)


class TestConfirmEmailVerificationView:
    path = "/users/email-verification/confirm"
    def test_confirm_email_verification_successful(self, user: User, client: IsClient):
        """
        link in the email can be parsed once it hits the backend.
        email already has been checked for correct tokens and uidb64.
        So in this view i just test the view.
        """

        from leasify.authentication.tokens import uidb64_generate, token_generate

        path = self.path + uidb64_generate(user) + "/" + token_generate(user)
        res = client.post(path, {})
        parse_message(res)
        user.refresh_from_db()  # type: ignore
        assert user.verified == True


class TestRequestPasswordResetView:
    path = "/auth/password-reset/request"

    def test_password_reset_successful(self, user: User, client: IsClient, mailoutbox: list[EmailMessage], cache_clear):
        """
        Check the mail is sent and contains the associated links.
        Should work with unauthenticated users as they try to recover their accounts
        """

        res1 = client.post(self.path, {"email": user.email})
        parse_message(res1, status.HTTP_202_ACCEPTED)
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [user.email]
        check_links_in_mail(user, mail, "password-reset")

    def test_email_normalization(self, user: User, client: IsClient, mailoutbox: list[EmailMessage], cache_clear):
        """
        Check the mail is sent and contains the associated links.
        Should work with unauthenticated users as they try to recover their accounts
        """

        parts = user.email.split("@")
        email = "@".join(parts)
        res1 = client.post(self.path, {"email": email})
        parse_message(res1, status.HTTP_202_ACCEPTED)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]

    def test_throttles_based_on_email(self, user: User, client: IsClient, override_throttles, cache_clear):
        """
        Should throttle based on the email address provided in the request body.
        """

        res1 = client.post(self.path, {"email": user.email})
        parse_message(res1, status.HTTP_202_ACCEPTED)

        res2 = client.post(self.path, {"email": user.email})
        errs2 = parse_error(res2, status.HTTP_429_TOO_MANY_REQUESTS)
        assert errs2[0]["code"] == "throttled"

    def test_wrong_email_formats_fail(self, client: IsClient, mailoutbox: list[EmailMessage]):
        """
        Wrong email formats should raise an error
        Should fail on not found emails but return uniform response
        """

        res1 = client.post(self.path, {"email": "email.com"})
        err1 = parse_error(res1, status.HTTP_400_BAD_REQUEST, "validation_error")
        assert err1[0]["attr"] == "email"

    def test_uniform_status_codes_even_for_unknown_emails(self, client: IsClient, mailoutbox: list[EmailMessage]):
        """
        Should fail on unregistered email but return uniform response
        """
        res1 = client.post(self.path, {"email": "test@email.com"})
        parse_message(res1, status.HTTP_202_ACCEPTED)
        assert len(mailoutbox) == 0


class TestConfirmPasswordResetView:
    path = "/users/password-reset/confirm"

    def test_confirm_password_reset_successfully_allows_password_to_be_reset(
        self, client: IsClient, user: User, password
    ):
        """
        Other logged in instances will be rendered unauthenticated.
        Will use a client to ensure unauthenticated requests are allowed.
        """

        from leasify.authentication.tokens import token_generate, uidb64_generate
        from rest_framework.test import APIClient

        # First create a logged in instance of a client
        logged_in = APIClient()
        res1 = logged_in.post("/auth/login", {"email": user.email, "password": password})
        parse_message(res1)  # type: ignore

        # stale user instance leads to generation of invalid tokens
        user.refresh_from_db()  # type: ignore

        # reset the password
        token = token_generate(user)
        path = "/".join([self.path, uidb64_generate(user), token])
        new_password = "NewPa55word!!"

        res2 = client.post(path, {"new_password": new_password, "confirm_password": new_password})
        parse_message(res2)

        user.refresh_from_db()  # type: ignore
        user.validate_password(new_password)

        # Try to access auth routes with previous session
        res3 = logged_in.post("/users/me", {})
        parse_error(res3, status.HTTP_401_UNAUTHORIZED)  # type: ignore
