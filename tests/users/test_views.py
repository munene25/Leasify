import pytest
from rest_framework import exceptions, status
from rest_framework.response import Response
from users.models import User, Account
from unittest.mock import patch, MagicMock


@pytest.fixture()
def override_throttles(settings):
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
        "anon_sustained": "1/min",
        "user_sustained": "1/min",
        "login_limit": "1/min",
        "password_changes": "1/min",
        "email_verification": "1/min",
        "email_change": "1/day",
    }


class TestUserListCreateView:
    def test_post_user_creation_successful(self, client, mailoutbox, user_create_payload, django_capture_on_commit_callbacks):
        payload = user_create_payload
        payload["notify"] = True
        with django_capture_on_commit_callbacks() as callback:
            response: Response = client.post("/api/users/", payload)
        assert len(callback) == 1
        callback[0]()
        # response body should be as expected
        assert response.status_code == status.HTTP_201_CREATED
        assert "user account created" in str(response.data)
        
        fetched = User.objects.get(email=payload["email"])
        
        # Password should be hashed and user should be able to authenticate
        assert fetched.password != payload["password"]
        assert fetched.check_password(payload["password"])
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [payload["email"]]

