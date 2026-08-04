from unittest.mock import patch, MagicMock

import pytest
from freezegun import freeze_time

from django.utils import timezone
from django.core.cache import cache
from django.db.models import QuerySet
from django.urls import reverse
from django.core.mail import EmailMessage
from rest_framework import status

from leasify.users.models import User, Account, EMAIL_COOLDOWN
from leasify.tests.types import IsClient, Factory
from leasify.tests.helpers import parse_error, parse_message, parse_paginated_response, check_links_in_mail


class TestUserListCreateView:
    path = reverse("users:list_create")

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
    def test_authentication_and_authorization(self, _client: str, get: int, post: int, request: pytest.FixtureRequest):
        """Verify auth and permissions for user list."""
        client: IsClient = request.getfixturevalue(_client)
        assert client.get(self.path).status_code == get
        assert client.post(self.path, self.payload).status_code == post


    def test_user_creation_successful(
        self,
        client: IsClient,
        mailoutbox: list[EmailMessage],
        django_capture_on_commit_callbacks,
    ):
        """User should be created and password hashed and can be used to login"""
        payload = {
            **self.payload,
            "notify": True,
            "unsubscribe_url": "path/to/unsubscribe",
            "email_verify_url": "path/to/verify"
        }
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(self.path, payload)

        data = parse_message(response, status.HTTP_201_CREATED)

        user = User.objects.get(email=payload["email"])

        # Password should be hashed and user should be able to authenticate
        assert "password" not in data and payload["password"] != user.password
        assert user.verified == False

        # Should be able to athenticate
        assert data["email"] == payload["email"]
        client.login(email=data["email"], password=payload["password"])

        # Assert mail is sent
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [payload["email"]]
        check_links_in_mail(path=payload["unsubscribe_url"], mail=mail, with_uidb64=True, user=user)
        check_links_in_mail(path=payload["email_verify_url"], mail=mail, with_uidb64=True, with_token=True, user=user)

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

    @patch("users.services.create.user_account_create", return_value=User(pk=1, account=Account(pk=1)))
    def test_user_creation_throttles(self, mock: MagicMock, client: IsClient, cache_clear, override_throttles):
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
        assert mock.call_count == 1
        assert errors["code"] == "throttled"


    def test_user_list_pagination(self, manager_client: IsClient, user_factory: Factory[User], override_pagination: int):
        """
        Test the pagination structure and data
        Order is reversed so the first user appears in the last index
        """
        user_factory(3)
        response1 = manager_client.get(self.path + "?page=1")
        parse_paginated_response(response1,  4)

    @pytest.mark.parametrize(
        "query,filters",
        [
            ("is_active=false", {"is_active": False}),
            ("search=Felix", {"search": "Felix"}),
            ("search=test@example.com", {"search": "test@example.com"}),
            ("search=1234", {"search": "1234"}),
            (
                "search=Felix&is_active=false",
                {"search": "Felix", "is_active": False},
            ),
        ],
    )
    @patch("leasify.users.selectors.user_list_for", return_value=QuerySet(User))
    def test_list_filtering(self, mock_list, caretaker_client: IsClient, query: str, filters: dict):
        caretaker_client.get(f"{self.path}?{query}")

        mock_list.assert_called_once_with(
            caretaker_client.user,
            filters
        )

    def test_user_list_ommits_results_from_qs_correctly(
        self,
        user_factory: Factory[User],
        caretaker_user: User,
        caretaker_client: IsClient,
        manager_user: User,
        manager_client: IsClient,
        superuser_client: IsClient,
    ):
        """
        The list qs should ommit certain types of users based on the fetching user priviledges
        """
        from leasify.users.selectors import get_group

        new_user: User = user_factory()[0]
        new_user.groups.add(get_group(name="manager"))

        # Super user should view 3 users excluding themselves
        respnse1 = superuser_client.get(self.path)
        data1 = parse_message(respnse1)["results"]
        assert len(data1) == 3
        assert {new_user.pk, caretaker_user.pk, manager_user.pk} == {f["user_id"] for f in data1}

        # Manager user should be able to view other managers, caretakers, ommits superusers
        # Only caretaker and new_user should appear
        response2 = manager_client.get(self.path)
        data2 = parse_message(response2)["results"]
        assert len(data2) == 2
        assert {new_user.pk, caretaker_user.pk} == {f["user_id"] for f in data2}

        response3 = caretaker_client.get(self.path)
        data3 = parse_message(response3)
        assert len(data3["results"]) == 0


class TestAdminUserDetailUpdateDestroyView:
    path: str = "/users/"

    def test_user_detail_succeeds(self, user_create_payload, user: User, manager_client: IsClient):
        """
        test for get, patch and delete routes success in one place
        """

        # -- Test get data is accurate --
        pld = user_create_payload
        path = self.path + str(user.pk)
        response1 = manager_client.get(path)
        data1 = parse_message(response1)
        assert data1["user_id"] == user.pk
        assert data1["email"] == user.email
        assert data1["first_name"] == user.first_name
        assert data1["last_name"] == user.last_name
        assert data1["bio"] == user.account.bio
        assert data1["phone_number"] == str(user.account.phone_number)

        # -- Test patching data succeds --
        pld["phone_number"] = "254720202202"
        response2 = manager_client.patch(path, pld)
        data2 = parse_message(response2)
        fetched = User.objects.get(pk=user.pk)
        assert fetched.email == data2["email"]
        assert data2["user_id"] == fetched.pk
        assert data2["phone_number"] == fetched.account.phone_number == pld["phone_number"]
        assert data2["first_name"] == fetched.first_name == pld["first_name"]
        assert data2["last_name"] == fetched.last_name == pld["last_name"]

        reponse3 = manager_client.delete(path)
        parse_message(reponse3)
        fetched2 = User.objects.get(pk=user.pk)
        assert fetched2.is_active == False

    def test_user_detail_view_authentication(self, user_client: IsClient, caretaker_client: IsClient):
        """
        Pemission denied for regular users
        Patch and delete should raise permission denied for caretakers
        """
        status_code = status.HTTP_403_FORBIDDEN
        path = self.path + "1"

        response1 = user_client.get(path)
        error1 = parse_error(response1, status_code)[0]
        assert error1["code"] == "permission_denied"

        response2 = caretaker_client.get(path)
        data2 = parse_message(response2)
        assert data2["email"] == User.objects.get(pk=1).email

        response3 = caretaker_client.patch(path, {"first_name": "Felix"})
        error3 = parse_error(response3, status_code)[0]
        assert error3["code"] == "permission_denied"

        respnse4 = caretaker_client.delete(path)
        errors4 = parse_error(respnse4, status_code)[0]
        assert errors4["code"] == "permission_denied"

        response5 = user_client.patch(path, {"first_name": "Felix"})
        error5 = parse_error(response5, status_code)[0]
        assert error5["code"] == "permission_denied"

        response5 = user_client.delete(path)
        error5 = parse_error(response5, status_code)[0]
        assert error5["code"] == "permission_denied"

    def test_modifying_priviledged_users_fails(self, manager_client: IsClient, superuser: User):
        """
        Priviledged users can't be modified or retrieved
        """
        status_code = status.HTTP_404_NOT_FOUND
        path = self.path + str(superuser.pk)

        response1 = manager_client.get(path)
        error1 = parse_error(response1, status_code)[0]
        assert error1["code"] == "not_found"

        response2 = manager_client.patch(path, {"first_name": "first"})
        error2 = parse_error(response2, status_code)[0]
        assert error2["code"] == "not_found"

        response3 = manager_client.delete(path)
        error3 = parse_error(response3, status_code)[0]
        assert error3["code"] == "not_found"


class TestMeView:
    path = reverse("users:me")

    def test_user_can_get_patch_and_delete_successfully(self, user: User, client: IsClient, password: str):
        """
        Users should be able to get correct data
        No user_id should be present in the serializer
        Users should be able modify the specified fields

        Bug fixed: was passing the request.user into logout
        Fixed: With custom auth class, 401 is raised
        """
        logged_in = client.login(email=user.email, password=password)
        assert logged_in == True
        response1 = client.get(self.path)
        data1 = parse_message(response1)

        # User id should not be visible
        assert data1.get("user_id", None) is None
        assert data1["first_name"] == user.first_name
        assert data1["last_name"] == user.last_name
        assert data1["email_verified"] == user.verified
        assert data1["backup_email"] == user.account.backup_email
        assert data1["phone_number"] == str(user.account.phone_number)
        assert data1["next_email_change"] == None
        assert data1["role"] == "regular"

        updates = {
            "first_name": "Zane",
            "email": "testemail1@gmail.com",
            "phone_number": "+254 710 111 110",
            "bio": "A regular bio",
            "role": "manager",
        }
        response2 = client.patch(self.path, updates)
        data2 = parse_message(response2)
        user.refresh_from_db()  # type: ignore
        assert data2.get("user_id", None) is None
        assert data2["first_name"] == updates["first_name"] == user.first_name
        assert (
            data2["phone_number"]
            == updates["phone_number"].replace(" ", "").replace("+", "")
            == user.account.phone_number
        )
        assert data2["bio"] == updates["bio"] == user.account.bio
        assert data2["email"] != updates["email"] and data2["email"] == user.email
        assert data2["role"] != updates["role"] and data2["role"] == "regular"

        # Unauthorized will be raised
        response3 = client.delete(self.path)
        data = parse_message(response3, status.HTTP_204_NO_CONTENT)
        assert data["message"] == "account deactivated successfully"
        user.refresh_from_db()  # type: ignore
        assert user.is_active == False
        response4 = client.get(self.path)
        error = parse_error(response4, status.HTTP_401_UNAUTHORIZED)[0]
        assert error["code"] == "not_authenticated"

    def test_unauthenticated_requests_fail(self, client: IsClient):
        """
        Should outright deny services for users with"""
        response1 = client.get(self.path)
        error1 = parse_error(response1, status_code=status.HTTP_401_UNAUTHORIZED)[0]
        assert error1["code"] == "not_authenticated"


class TestEmailUpdateView:
    path = "/users/email-change"
    payload = {"email": "test@gmail.com", "password": "Pa55word!"}

    before = timezone.now()
    after = before + EMAIL_COOLDOWN

    def test_email_updates_successfully(self, user: User, user_client: IsClient):
        """
        Email should be upddated correctly
        Next change should be denied
        Response should include New email
        """

        with freeze_time(self.before) as frozen:
            fetch = lambda: user_client.post(self.path, self.payload)
            data1 = parse_message(fetch())
            user.refresh_from_db()  # type: ignore
            assert data1["email"] == self.payload["email"] == user.email
            assert user.next_email_change == self.after

            frozen.move_to(self.after)
            parse_message(fetch())
            user.refresh_from_db
            assert user.next_email_change == self.after + EMAIL_COOLDOWN

    def test_email_update_fails(self, user, client: IsClient, user_client: IsClient):
        """
        Fails for unauthenticated reqs
        Fails for Wrong password
        """
        # -- with unauthenticated requests raises 401 --
        res1 = client.post(self.path, {})
        parse_error(res1, status.HTTP_401_UNAUTHORIZED)

        # -- with wrong passwords fails with validation error --
        res2 = user_client.post(self.path, {**self.payload, "password": "pass"})
        error = parse_error(res2, status.HTTP_400_BAD_REQUEST, "validation_error")
        assert "password" == error[0]["attr"]

        # -- When cooldown is still active fails with 400 --
        with freeze_time(self.before) as frozen:
            res3 = user_client.post(self.path, self.payload)
            parse_message(res3)

            frozen.move_to(timezone.now() + 0.5 * EMAIL_COOLDOWN)
            res4 = user_client.post(self.path, self.payload)
            parse_error(res4, status.HTTP_422_UNPROCESSABLE_ENTITY)
            user.refresh_from_db
            assert user.last_email_change == self.before


class TestUserUnsubscribeView:
    path = "/users/unsubscribe/"

    def test_unsubscribe_successful(self, client: IsClient, user: User):
        """
        With the correct link, users should be able to unsubscribe from emails.
        No authentication is required. uidb64 is used to identify the user.
        The account's can_receive_emails field should be set to false

        Bug fixed: was checking the wrong state for the account before calling service.
        """
        from leasify.authentication.tokens import uidb64_generate

        path = self.path + uidb64_generate(user)
        response = client.post(path, {})
        parse_message(response)
        user.refresh_from_db()  # type: ignore
        assert user.account.can_receive_emails == False

    def test_unsubscribe_with_invalid_link_fails(self, client: IsClient, user: User):
        """
        With an invalid link, the request should be denied and no accounts should be modified.
        """
        response = client.post(self.path + "invalidlink", {})
        parse_error(response, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()  # type: ignore
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
