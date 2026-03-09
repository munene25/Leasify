import pytest
from users.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework.exceptions import AuthenticationFailed
from users.services import user_login

class TestLoginService:
    def test_login_service_succeeds(self, user: User):
        """
        credentials passed should correctly return an authenticated user
        last_login field should be updated
        returned user should be the match
        """
        authenticated_user = user_login(email=user.email, password="Pa55word!")
        assert authenticated_user == user
        assert authenticated_user.last_login is not None
        timesince = authenticated_user.last_login - timezone.now()
        assert timesince <= timedelta(seconds=1)

    def test_login_service_fails_with_inactive_users(self, user: User):
        user.is_active = False
        user.save(update_fields=["is_active"])

        with pytest.raises(AuthenticationFailed) as exc:
            user_login(email=user.email, password="Pa55word!")
        assert "email" in exc.value.detail and "password" in exc.value.detail

    def test_login_fails_for_wrong_credentials(self, user: User):
        wrong_email = "test@testemail.com"
        wrong_pass = "password"
        with pytest.raises(AuthenticationFailed) as exc:
            user_login(email=wrong_email, password=wrong_pass)
        assert "email" in exc.value.detail and "password" in exc.value.detail
    
    def test_login_succeds_with_normalization(self, user: User):
        """
        User lookups should use normalized emails
        """
        parts = user.email.split("@")
        email = parts[0] + "@" +parts[1].upper()
        authd_user = user_login(email=email, password="Pa55word!")
        assert authd_user == user