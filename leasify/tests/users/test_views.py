import pytest
from copy import deepcopy

from unittest.mock import patch, MagicMock
from freezegun import freeze_time

from django.utils import timezone
from django.core.cache import cache
from django.core.mail import EmailMessage
from rest_framework import status

from leasify.users.models import User, EMAIL_COOLDOWN
from leasify.tests.types import IsClient, UserCreatePayload, Factory
from leasify.tests.helpers import parse_error, parse_message, parse_paginated_response


class TestUserListCreateView:
    path = "/users/"

    def test_user_creation_successful(
        self,
        client: IsClient,
        mailoutbox: list[EmailMessage],
        user_create_payload: UserCreatePayload,
        django_capture_on_commit_callbacks,
    ):
        """
        User should be created and password hashed and can be used to login
        """
        payload = user_create_payload
        payload["notify"] = True
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(self.path, payload)

        # Assert response format
        assert response.status_code == status.HTTP_201_CREATED

        fetched = User.objects.get(email=payload["email"])

        # Password should be hashed and user should be able to authenticate
        assert fetched.password != payload["password"]
        assert fetched.check_password(payload["password"])

        # Assert other fields
        assert fetched.email == payload["email"]
        assert fetched.verified == False

        # Assert mail is sent
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [payload["email"]]

    @pytest.mark.parametrize(
        "field,value",
        [
            ("phone_number", "0710 100 100"),
            ("email", "felix@gmail.com"),
        ],
    )
    def test_user_creation_fails_for_db_constraints(self, cache_clear, field: str, value: str, client: IsClient):
        """
        Similar email and phone number should raise 400
        """
        defaults = {"first_name": "test", "last_name": "test", "password": "Pa55word!", "notify": False}
        payload1 = {**defaults, "phone_number": "0710 100 100", "email": "test1@gmail.com"}
        payload2 = {**defaults, "phone_number": "0720 200 200", "email": "test2@gmail.com"}

        payload1[field] = payload2[field] = value
        client.post(self.path, payload1)

        response2 = client.post(self.path, payload2)
        errors = parse_error(response2, status.HTTP_400_BAD_REQUEST, "validation_error")[0]
        assert errors["attr"] == field
        assert errors["code"] == "invalid"

    def test_user_creation_fails_for_wrong_field_formats(
        self, client: IsClient, user_create_payload: UserCreatePayload
    ):
        """
        Using a regular client implicitly tests authentication as well
        """
        # -- with wrong phone nubmer fmt fails --

        payload1 = deepcopy(user_create_payload)
        payload1["phone_number"] = "077171"  # type: ignore : Technically can use a str
        response = client.post(self.path, payload1)
        errors = parse_error(response, status.HTTP_400_BAD_REQUEST, "validation_error")[0]
        assert errors["code"] == "invalid"
        assert errors["attr"] == "phone_number"

        # -- Fails for a short names, both fields should appear in the error dict --
        payload2 = deepcopy(user_create_payload)
        payload2["first_name"] = "F"
        payload2["last_name"] = "F"

        response2 = client.post(self.path, payload2)
        errors = parse_error(response2, status.HTTP_400_BAD_REQUEST, "validation_error", err_len=2)
        assert errors[0]["attr"] == "first_name"
        assert errors[1]["attr"] == "last_name"

        assert User.objects.count() == 0

    @patch("users.services.user_account_create")
    def test_user_creation_throttles(
        self,
        mock: MagicMock,
        client: IsClient,
        cache_clear,
        override_throttles,
        user_create_payload: UserCreatePayload,
    ):
        """
        Patch the account create func to speed up
        Throttle the second request, the first and last should be okay
        """
        # -- with first request should succeed --
        response = client.post(self.path, user_create_payload)
        assert response.status_code == status.HTTP_201_CREATED

        # -- with second request should throttle --
        response2 = client.post(self.path, user_create_payload)
        errors = parse_error(response2, status.HTTP_429_TOO_MANY_REQUESTS)[0]
        assert mock.call_count == 1
        assert errors["code"] == "throttled"

        # -- With third request should succeed after clearing cache
        cache.clear()
        response3 = client.post(self.path, user_create_payload)

        assert response3.status_code == status.HTTP_201_CREATED
        assert mock.call_count == 2

    def test_user_list_authentication_and_authorization(
        self, cache_clear, client: IsClient, manager_client: IsClient, tenant_client: IsClient
    ):
        """
        No authentication class on the view
        Authentication is handled after the view instantiates
        Permission denied 403: authenticated but unauthorized users
        Authentication failed 401: unauthenticated users
        ! With Session Authentication, 401 errors are coerced into 403
        """

        # -- with unauthenticated user should raise Unauthorized --
        response = client.get(self.path)
        # Unauthorized should be raised for unauthenticated
        errors = parse_error(response, status.HTTP_401_UNAUTHORIZED)[0]
        assert errors["code"] == "not_authenticated"
        assert errors["detail"] == "Authentication credentials were not provided."

        # -- with an authenticated but unauthorized user should raise 403 --
        response2 = tenant_client.get(self.path)
        errors2 = parse_error(response2, status.HTTP_403_FORBIDDEN)[0]
        assert errors2["code"] == "permission_denied"

        # -- with an authorized user with sufficient permission should pass --
        response3 = manager_client.get(self.path)
        assert response3.status_code == status.HTTP_200_OK

    def test_user_list_pagination(self, manager_client: IsClient, user_factory: Factory[User], override_pagination: int):
        """
        Test the pagination structure and data
        Order is reversed so the first user appears in the last index
        """

        # The creation of a manager client has created a new user in the db
        # but would still be filtered out
        expected_users = 3
        users = user_factory(expected_users)
        first_page_ids = {u.pk for u in users[-override_pagination:]}
        second_page_ids = {u.pk for u in users}.difference(first_page_ids)

        path = lambda page: f"{self.path}?page={page}"

        # -- First page --
        response1 = manager_client.get(path(1))
        data1 = parse_paginated_response(response1, expected_users)
        assert first_page_ids == {f["user_id"] for f in data1["results"]}

        # -- Next page --
        response2 = manager_client.get(path(2))
        data2 = parse_paginated_response(response2, expected_users)
        assert data2["next"] == None
        assert {f["user_id"] for f in data2["results"]} == second_page_ids

    def test_user_list_filtering_via_query_params(self, user_factory: Factory[User], caretaker_client: IsClient):
        """
        Test the new search field implementation for the query_params
        Fields: id, is_active and search(includes all searchable fields)
        """
        from leasify.tests.helpers import parse_paginated_response

        path = lambda query: f"{self.path}?{query}"

        users = user_factory(5)

        # -- Create inactive users
        inactive_user_ids = {3, 2, 4}
        User.objects.filter(id__in=inactive_user_ids).update(is_active=False)

        # -- create users sharing first name
        similar_name_ids = {4, 6}
        similar_name = "Felix"
        User.objects.filter(id__in=similar_name_ids).update(first_name=similar_name)

        # -- Test is_active filter --
        response1 = caretaker_client.get(path("is_active=false"))
        data1 = parse_paginated_response(response1, 3)["results"]
        assert inactive_user_ids == {u["user_id"] for u in data1}

        # -- with last_name search filtering --
        response2 = caretaker_client.get(path(f"search={users[0].last_name}"))
        data2 = parse_paginated_response(response2, 1)["results"]
        assert users[0].pk in {u["user_id"] for u in data2}

        response3 = caretaker_client.get(path(f"search={similar_name}"))
        data3 = parse_paginated_response(response3, 2)["results"]
        assert similar_name_ids == {u["user_id"] for u in data3}

        # -- with phone_number search filtering --
        phone_number = users[0].account.phone_number
        sliced_phone = str(phone_number)[-4:]
        data4 = parse_paginated_response(caretaker_client.get(path(f"search={sliced_phone}")), 1)["results"]
        assert data4[0]["user_id"] == users[0].pk

        # -- with exact fields (email) search filtering --
        data5 = parse_paginated_response(caretaker_client.get(path(f"search={users[3].email}")), 1)["results"]
        assert users[3].email == data5[0]["email"]

        # -- with multiple field searches --
        # user_id 4 is the only user with the name Felix and is in_active
        response6 = caretaker_client.get(path(f"search={similar_name}&is_active=false"))
        data6 = parse_paginated_response(response6, 1)["results"]
        assert data6[0]["user_id"] == 4

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
    path = "/users/me"

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
        monkeypatch.setattr("users.selectors.groups_list", lambda: [])
        response1 = manager_client.get(self.path, {})
        data1 = parse_message(response1)
        assert len(data1["roles"]) == 0

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
