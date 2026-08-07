from unittest.mock import patch, MagicMock

import pytest
from freezegun import freeze_time

from django.utils import timezone
from django.db.models import QuerySet
from django.urls import reverse
from rest_framework import status

from leasify.users.models import User, Account, EMAIL_COOLDOWN
from leasify.users.choices import AccountType
from leasify.tests.types import IsClient, Factory
from leasify.tests.helpers import parse_error, parse_message, parse_paginated_response, check_links_in_mail


class TestUserListCreateView:

    path = reverse("users:list_create")
    patch_create = patch("leasify.users.services.create.user_create", return_value=User(pk=1, account=Account(pk=1)))
    patch_list_for = patch("leasify.users.selectors.user_list_for", return_value=QuerySet(User))

    payload = {
            "first_name": "Test",
            "last_name": "Test",
            "email": "test@mail.com",
            "password": "Pa55word!",
            "phone_number": "254710100100",
            "notify": False
        }

    @pytest.mark.parametrize(
        "_client,get,post",
        [
            ("superuser_client", 200, 201),
            ("manager_client", 200, 201),
            ("caretaker_client", 200, 201),
            ("tenant_client", 403, 201),
            ("user_client", 403, 201),
            ("client", 401, 201),
        ],
    )
    @patch_create
    def test_authentication_and_authorization(self, patch_create: MagicMock, _client: str, get: int, post: int, request: pytest.FixtureRequest):
        """Verify auth and permissions for user list."""
        client: IsClient = request.getfixturevalue(_client)
        assert client.get(self.path).status_code == get
        assert client.post(self.path, self.payload).status_code == post


    def test_user_creation_successful(self, client: IsClient, django_capture_on_commit_callbacks):
        """User should be created and password hashed and can be used to login"""
        
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(self.path, self.payload)

        data = parse_message(response, status.HTTP_201_CREATED)
        user = User.objects.get(email=self.payload["email"])
        assert user.is_active == True
        assert user.is_staff == False
        assert user.is_superuser == False

        # Password should be hashed and user should be able to authenticate
        assert "password" not in data and self.payload["password"] != user.password

        # Should be able to athenticate
        assert data["email"] == self.payload["email"]
        client.login(email=data["email"], password=self.payload["password"])

    @patch_create
    def test_mock_call(self, patch_create: MagicMock, client: IsClient):
        """Assert user_account_create is called with correct arguments"""

        payload = {
            **self.payload,
            "notify": True,
            "unsubscribe_url": "path/to/unsubscribe",
            "email_verify_url": "path/to/verify"
        }
        parse_message(client.post(self.path, payload), 201)
        patch_create.assert_called_once_with(**payload, is_active=True, is_superuser=False, is_staff=False, account_type=AccountType.EMAIL)

    @pytest.mark.parametrize(
        "field,value,code",
        [
            ("phone_number", "077171", "invalid"),
            ("first_name", "F", "min_length"),
            ("last_name", "F", "min_length"),
        ],
    )
    def test_create_serializer(self, client: IsClient, field: str, value: str, code: str):
        """Invalid serializer fields should fail validation."""
        response = client.post(self.path, {**self.payload, field: value})

        error = parse_error(response, status.HTTP_400_BAD_REQUEST, "validation_error",)[0]

        assert error["attr"] == field
        assert error["code"] == code
        assert User.objects.count() == 0

    @patch_create
    def test_user_creation_throttles(self, patch_create: MagicMock, client: IsClient, cache_clear, override_throttles):
        """
        Patch the account create func to speed up
        Throttle the second request, the first and last should be okay
        """
        # -- with first request should succeed --
        response = client.post(self.path, self.payload)
        assert response.status_code == status.HTTP_201_CREATED

        # -- with second request should throttle --
        response2 = client.post(self.path, self.payload)
        errors = parse_error(response2, status.HTTP_429_TOO_MANY_REQUESTS)[0]
        assert patch_create.call_count == 1
        assert errors["code"] == "throttled"


    def test_user_list_pagination(self, manager_client: IsClient, user_factory: Factory[User], override_pagination: int):
        """Should be paginated, expected users ommits the requesting user"""
        user_factory(3)
        response1 = manager_client.get(self.path + "?page=1")
        parse_paginated_response(response1,  3)

    @pytest.mark.parametrize(
        "query,filters",
        [
            ("is_active=false", {"is_active": False}),
            ("search=Felix", {"search": "Felix"}),
            ("search=test@example.com", {"search": "test@example.com"}),
            ("search=1234", {"search": "1234"}),
            ("search=Felix&is_active=false", {"search": "Felix", "is_active": False},
            ),
        ],
    )
    @patch_list_for
    def test_list_filtering(self, patch_list_for: MagicMock, caretaker_client: IsClient, query: str, filters: dict):
        caretaker_client.get(f"{self.path}?{query}")

        patch_list_for.assert_called_once_with(
            user=caretaker_client.user,
            filters=filters
        )


class TestAdminUserDetailUpdateDestroyView:
    patch_get_for = patch("leasify.users.selectors.user_get_for", return_value=User(pk=1, account=Account()))
    patch_update_status = patch("leasify.users.services.update.user_update_active_status", return_value=User(pk=1, account=Account()))

    def path(self, *args: int) -> str:
        return reverse("users:admin_detail", args=args)
    
    @pytest.mark.parametrize(
        "_client,get,delete",
        [
            ("superuser_client", 200, 200),
            ("manager_client", 200, 200),
            ("caretaker_client", 200, 403),
            ("tenant_client", 403, 403),
            ("user_client", 403, 403),
            ("client", 401, 401),
        ],
    )
    @patch_get_for
    def test_authentication_and_authorization(self, patch_get_for: MagicMock, _client: str, get: int, delete: int, request: pytest.FixtureRequest):
        """Verify auth and permissions for user list."""
        client: IsClient = request.getfixturevalue(_client)
        assert client.get(self.path(1)).status_code == get
        assert client.delete(self.path(1)).status_code == delete
    
    def test_user_detail_succeeds(self, user: User, manager_client: IsClient):
        """Test user detail"""
        # -- Test get data is accurate --
        path = self.path(user.pk)
        response1 = manager_client.get(path)
        data1 = parse_message(response1)
        assert data1["user_id"] == user.pk
        assert data1["email"] == user.email
        assert data1["first_name"] == user.first_name
        assert data1["last_name"] == user.last_name
        assert data1["account_type"] == user.account.type
        assert data1["phone_number"] == str(user.account.phone_number)


    def test_deactivate_user(self, manager_client: IsClient, user: User):
        """Deactivating user should work as expected"""
        path = self.path(user.pk)
        response = manager_client.delete(path)
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active == False

    @patch_get_for
    def test_get_mock_calls(self, patch_get_for: MagicMock, user: User, manager_client: IsClient):
        """Get and delete should use user_get_for and updating status should be called in delete"""
        manager_client.get(self.path(user.pk))
        patch_get_for.assert_called_once_with(user=manager_client.user, user_id=user.pk)

    @patch_get_for
    @patch_update_status
    def test_delete_mock_calls(self, patch_update_status: MagicMock, patch_get_for: MagicMock, manager_client: IsClient):
        """Get and delete should use user_get_for and updating status should be called in delete"""
        manager_client.delete(self.path(1))
        patch_get_for.assert_called_once_with(user=manager_client.user, user_id=1)
        patch_update_status.assert_called_once_with(user=patch_get_for.return_value, status=False)

class TestMeView:
    path = reverse("users:me")

    patch_update_user = patch("leasify.users.services.update.user_update", return_value=User(pk=1, account=Account()))
    patch_update_status = patch("leasify.users.services.update.user_update_active_status", return_value=User(pk=1, account=Account()))


    payload = {
        "first_name": "Zane",
        "last_name": "Omondi",
        "phone_number": "+254 710 111 110",
        "backup_email": "test@test.com"
    }

    def test_authentication_and_authorization(self, client: IsClient, ):
        """Unauthenticated users not allowed."""
        assert client.get(self.path).status_code == status.HTTP_401_UNAUTHORIZED
        assert client.patch(self.path, self.payload).status_code == status.HTTP_401_UNAUTHORIZED
        assert client.delete(self.path).status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_data(self, user_client: IsClient):
        """Should retrun the users own data"""
        user = user_client.user
        data = parse_message(user_client.get(self.path))

        assert data["user_id"] == user.pk
        assert data["first_name"] == user.first_name
        assert data["last_name"] == user.last_name
        assert data["email_verified"] == user.verified
        assert data["backup_email"] == user.account.backup_email
        assert data["phone_number"] == str(user.account.phone_number)
        assert data["next_email_change"] == None
        assert data["role"] == "regular"

    @patch_update_user
    def test_modifying_data(self, patch_update_user: MagicMock, user_client: IsClient):
        """Should retrun the users own data"""
        user_client.patch(self.path, self.payload)
    
        kwargs = patch_update_user.call_args.kwargs 
        assert kwargs["user"].email == user_client.user.email
        assert kwargs["first_name"] == self.payload["first_name"]
        assert len(kwargs) == len(self.payload) + 1

    def test_deactivate_user(self, user_client: IsClient):
        """Should delete data and call logout"""
        from django.contrib.sessions.backends.db import SessionStore

        cookie = user_client.cookies["sessionid"]
        user_client.delete(self.path)

        user = user_client.user
        user.refresh_from_db()
        assert user.is_active == False
        assert not SessionStore().exists(cookie)
        assert user_client.get(reverse("users:me")).status_code == 401
        
    


class TestEmailUpdateView:
    path = reverse("users:email_change")
    payload = {"email": "test@gmail.com", "password": "Pa55word!"}
    

    def test_authentication(self, client: IsClient):
        """Fails for unauthenticated clients"""
        parse_error(client.post(self.path, {}), status.HTTP_401_UNAUTHORIZED)

    def test_email_updates_successfully(self, user_client: IsClient):
        """
        Email should be upddated correctly
        Response should include New email
        """
        now = timezone.now()
        with freeze_time(now):
            fetch = lambda: user_client.post(self.path, self.payload)
            user = user_client.user

            data1 = parse_message(fetch())
            user.refresh_from_db()  # type: ignore
            assert data1["email"] == self.payload["email"] == user.email
            assert user.next_email_change ==  now + EMAIL_COOLDOWN
        
    @pytest.mark.parametrize("override", [{"email": "email"}, {"password": "pas",}])
    def test_serializer(self, user_client: IsClient, override: dict):
        """Fails with status 400 for inavlid field values"""
        response =user_client.post(self.path, {**self.payload, **override})
        parse_error(response, status.HTTP_400_BAD_REQUEST, "validation_error")

class TestUserUnsubscribeView:
    def path(self, *args: str) -> str:
        return reverse("users:unsubscribe", args=args)

    def test_unsubscribe_successful(self, client: IsClient, user: User):
        """
        With the correct link, users should be able to unsubscribe from emails.
        No authentication is required. uidb64 is used to identify the user.
        The account's can_receive_emails field should be set to false

        Bug fixed: was checking the wrong state for the account before calling service.
        """
        from leasify.authentication.tokens import uidb64_generate

        path = self.path(uidb64_generate(user))
        response = client.post(path, {})
        parse_message(response)
        user.refresh_from_db()  # type: ignore
        assert user.account.can_receive_emails == False

    def test_unsubscribe_with_invalid_link_fails(self, client: IsClient, user: User):
        """With an invalid link, the request should be denied and no accounts should be modified."""
        path = self.path("invalidlink")
        response = client.post(path, {})
        parse_error(response, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        assert user.account.can_receive_emails == True


class TestAdminRoleListView:
    path = "/users/roles"

    def test_correct_response_with_available_group(self, manager_client: IsClient, roles_list):
        response1 = manager_client.get(self.path, {})
        data1 = parse_message(response1)
        assert len(data1) == len(roles_list)
        role = roles_list[0].name
        assert {"key": role, "display": role}

    def test_response_with_no_available_groups(self, manager_client: IsClient, monkeypatch):
        monkeypatch.setattr("leasify.users.selectors.groups_list", lambda: [])
        response1 = manager_client.get(self.path, {})
        data1 = parse_message(response1)
        assert len(data1) == 0

    def test_user_role_list_view_authentication_and_authorization(self, user_client: IsClient, caretaker_client: IsClient):
        """
        Pemission denied for regular users and caretakers
        """
        status_code = status.HTTP_403_FORBIDDEN

        response1 = user_client.get(self.path)
        error1 = parse_error(response1, status_code)[0]
        assert error1["code"] == "permission_denied"

        response2 = caretaker_client.get(self.path)
        error2 = parse_error(response2, status_code)[0]
        assert error2["code"] == "permission_denied"


class TestAdminRoleDetailView:
    path = "/users/roles/"

    def test_user_role_get_put_delete_successfully(self, manager_client: IsClient, user: User):
        """
        Manager should be able to view a user's roles, edit them and delete them.
        """
        # -- Test get data is accurate --
        path = self.path + str(user.pk)
        response1 = manager_client.get(path)
        data1 = parse_message(response1)
        assert data1["user_id"] == user.pk
        assert data1["role"] == "regular"

        # -- Test patching data succeeds --
        response2 = manager_client.patch(path, {"role": "manager"})
        data2 = parse_message(response2)
        user.refresh_from_db()  # type: ignore
        assert data2["user_id"] == user.pk
        assert data2["role"] == "manager"
        assert user.groups.filter(name="manager").exists() == True

        # -- Test deleting role succeeds --
        response3 = manager_client.delete(path)
        data3 = parse_message(response3)
        user.refresh_from_db()  # type: ignore
        assert data3["user_id"] == user.pk
        assert data3["role"] == "regular"
        assert user.groups.filter(name="manager").exists() == False

    def test_user_role_view_authentication_and_authorization(self, user_client: IsClient, caretaker_client: IsClient):
        """
        Pemission denied for regular users and caretakers
        """
        status_code = status.HTTP_403_FORBIDDEN
        path = self.path + "1"

        response1 = user_client.get(path)
        error1 = parse_error(response1, status_code)[0]
        assert error1["code"] == "permission_denied"

        response2 = caretaker_client.get(path)
        error2 = parse_error(response2, status_code)[0]
        assert error2["code"] == "permission_denied"

    def test_modifying_priviledged_users_fails(self, manager_client: IsClient, superuser: User):
        """
        Priviledged users can't have their roles modified or retrieved
        """
        status_code = status.HTTP_404_NOT_FOUND
        path = self.path + str(superuser.pk)

        response1 = manager_client.get(path)
        error1 = parse_error(response1, status_code)[0]
        assert error1["code"] == "not_found"

        response2 = manager_client.patch(path, {"role": "manager"})
        error2 = parse_error(response2, status_code)[0]
        assert error2["code"] == "not_found"

        response3 = manager_client.delete(path)
        error3 = parse_error(response3, status_code)[0]
        assert error3["code"] == "not_found"

    def test_patching_roles_replaces_the_assigned_role(self, manager_client: IsClient, user_factory: Factory[User]):
        """
        When patching a role, the existing role should be replaced with the new one.
        This prevents users from accumulating multiple roles unintentionally.
        """
        users: list[User] = user_factory(2)
        user = users[0]
        path = self.path + str(user.pk)

        # Assign manager role to the user
        response1 = manager_client.patch(path, {"role": "manager"})
        data1 = parse_message(response1)
        assert data1["role"] == "manager"
        user.refresh_from_db()  # type: ignore
        assert user.groups.filter(name="manager").exists() == True

        # Now assign caretaker role to the same user, which should replace the manager role
        response2 = manager_client.patch(path, {"role": "caretaker"})
        data2 = parse_message(response2)
        assert data2["role"] == "caretaker"
        user.refresh_from_db()  # type: ignore
        assert user.groups.count() == 1
        assert user.groups.filter(name="caretaker").exists() == True
        assert user.groups.filter(name="manager").exists() == False
