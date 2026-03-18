import pytest
from typing import Any
from rest_framework import status
from users.models import User, Account
from unittest.mock import patch, MagicMock
from copy import deepcopy
from django.core.cache import cache
from tests.types import IsClient, UserCreatePayload


@pytest.fixture(autouse=True)
def auto_clear(cache_clear):
    pass


def parse_error(response, status_code: int, err_type: str = "client_error", err_len: int = 1) -> list[dict[str, str]]:
    """
    Helper func parsing errors
    """
    assert response.status_code == status_code
    assert response.data["type"] == err_type
    errors: list[dict[str, str]] = response.data["errors"]
    assert len(errors) == err_len
    return errors


def parse_message(response, status_code: int = status.HTTP_200_OK) -> dict[str, Any]:
    """helper function"""
    assert response.status_code == status_code
    return response.data


class TestUserListCreateView:
    path = "/users/"

    def test_user_creation_successful(
        self,
        client: IsClient,
        mailoutbox: list,
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
    def test_user_creation_fails_for_db_constraints(self, field: str, value: str, client: IsClient):
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

    @patch("users.views.user_account_create")
    def test_user_creation_throttles(
        self,
        mock: MagicMock,
        override_throttles,
        client: IsClient,
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
        self, client: IsClient, manager_client: IsClient, tenant_client: IsClient
    ):
        """
        No authentication class on the view
        Authentication is handled after the view instantiates
        Permission denied 403: authenticated but unauthorized users

        Apparetntly once user is already authenticated, it does not matter what else is done, the response will be a 403
        """

        # -- with unauthenticated user should raise Unauthorized --
        response = client.get(self.path)
        # Unauthorized should be raised for unauthenticated
        errors = parse_error(response, status.HTTP_403_FORBIDDEN)[0]
        assert errors["code"] == "not_authenticated"
        assert errors["detail"] == "Authentication credentials were not provided."

        # -- with an authenticated but unauthorized user should raise 403 --
        response2 = tenant_client.get(self.path)
        errors2 = parse_error(response2, status.HTTP_403_FORBIDDEN)[0]
        assert errors2["code"] == "permission_denied"

        # -- with an authorized user with sufficient permission should pass --
        response3 = manager_client.get(self.path)
        assert response3.status_code == status.HTTP_200_OK

    def test_user_list_pagination(self, user_factory, manager_client: IsClient, override_pagination):
        """
        Test the pagination structure and data
        Order is reversed so the first user appears in the last index
        """

        total_users = 3
        base_url = "http://testserver/users/"

        users: list[User] = user_factory(total_users)
        first_user = users[-1]

        response1 = manager_client.get(self.path)
        data = parse_message(response1)

        count1 = data["count"]
        next1 = data["next"]
        previous1 = data["previous"]
        results1 = data["results"]

        # The manager client has created a new user in the db
        assert count1 == total_users

        assert next1 == f"{base_url}?page=2"
        assert previous1 == None
        assert len(results1) == override_pagination

        data1: dict = results1[0]
        assert data1["user_id"] == first_user.pk
        assert data1["email"] == first_user.email
        assert data1["phone_number"] == str(first_user.account.phone_number)

        # -- Next page --
        response2 = manager_client.get(next1)
        assert response2.status_code == status.HTTP_200_OK

        next2 = response2.data["next"]
        previous2 = response2.data["previous"]
        results2 = response2.data["results"]

        assert len(results2) == 1
        assert next2 == None
        assert previous2 == base_url

    def test_user_list_filtering_via_query_params(self, user_factory, caretaker_client: IsClient):
        """
        Test the new search field implementation for the query_params
        Fields: id, is_active and search(includes all searchable fields)
        """

        def fetch(field: str) -> list[dict[str, str]]:
            """helper function reduces boilerplate"""
            response = caretaker_client.get(f"{self.path}?{field}")
            assert response.status_code == status.HTTP_200_OK
            return response.data["results"]

        users: list[User] = user_factory(5)
        user1 = users[0]
        user3 = users[2]
        user5 = users[-1]
        user5.is_active = False
        user5.save()

        # -- with id filter --
        # ? ID filter temporarily removed, might reinstate
        # data1 = fetch("id=4")
        # assert len(data1) == 1
        # fetched = User.objects.get(pk=4)
        # assert data1[0]["user_id"] == 4
        # assert fetched.email == data1[0]["email"]

        # -- with is_active filter --
        data2 = fetch("is_active=false")
        assert len(data2) == 1
        assert data2[0]["email"] == user5.email

        # -- with name search filtering --
        sliced_name = user1.get_full_name()[:4]
        data3 = fetch(f"search={sliced_name}")
        assert len(data3) >= 1
        assert user1.pk in [user["user_id"] for user in data3]

        # -- with phone_number search filtering --
        sliced_phone = str(user3.account.phone_number)[:5]
        data4 = fetch(f"search={sliced_phone}")
        assert len(data4) >= 1
        assert user3.pk in [user["user_id"] for user in data4]

        # -- with exact fields (email) search filtering --
        data5 = fetch(f"search={user3.email}")
        assert len(data5) == 1
        assert user3.email == data5[0]["email"]

        # -- with multiple field searches --
        user4 = users[3]
        user4.first_name = user3.first_name
        user4.is_active = False
        user4.save()
        name, active = user3.first_name, True
        data6 = fetch(f"search={name}&is_active={active}")
        assert len(data6) == 1
        assert user3.email == data6[0]["email"]
        active = False
        data7 = fetch(f"search={name}&is_active={active}")
        assert len(data7) == 1
        assert user4.email == data7[0]["email"]

    def test_user_list_ommits_results_from_qs_correctly(
        self,
        user_factory,
        caretaker_user: User,
        caretaker_client: IsClient,
        manager_user: User,
        manager_client: IsClient,
        super_user_client: IsClient,
    ):
        """
        The list qs should ommit certain types of users based on the fetching user priviledges
        """
        from django.contrib.auth.models import Group

        new_user: User = user_factory()[0]
        new_user.groups.add(Group.objects.get(name="manager"))

        # Super user should view 3 users excluding themselves
        respnse1 = super_user_client.get(self.path)
        data1 = parse_message(respnse1)["results"]
        assert len(data1) == 3
        assert {new_user.pk, caretaker_user.pk, manager_user.pk} == {f["user_id"] for f in data1}

        # Manager user should be able to view other managers, caretakers, ommits super_users
        # Only caretaker and new_user should appear
        response2 = manager_client.get(self.path)
        data2 = parse_message(response2)["results"]
        assert len(data2) == 2
        assert {new_user.pk, caretaker_user.pk} == {f["user_id"] for f in data2}

        response3 = caretaker_client.get(self.path)
        data3 = parse_message(response3)
        assert len(data3["results"]) == 0


class TestUserDetailUpdateDestroyView:
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
        assert data1["email"] == user.email
        assert data1["first_name"] == user.first_name
        assert data1["last_name"] == user.last_name
        assert data1["bio"] == user.account.bio
        assert data1["phone_number"] == str(user.account.phone_number)

        # -- Test patching data succeds --
        pld["phone_number"] = "+254720202202"
        response2 = manager_client.patch(path, pld)
        data2 = parse_message(response2)
        fetched = User.objects.get(pk=user.pk)
        assert fetched.email == data2["email"]
        assert data2["phone_number"] == str(fetched.account.phone_number) == pld["phone_number"]
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

    def test_modifying_priviledged_users_fails(self, manager_client: IsClient, super_user):
        """
        Priviledged users can't be modified or retrieved
        """
        status_code = status.HTTP_404_NOT_FOUND
        path = self.path + str(super_user.pk)

        response1 = manager_client.get(path)
        error1 = parse_error(response1, status_code)[0]
        assert error1["code"] == "not_found"

        response2 = manager_client.patch(path, {"first_name": "first"})
        error2 = parse_error(response2, status_code)[0]
        assert error2["code"] == "not_found"

        response3 = manager_client.delete(path)
        error3 = parse_error(response3, status_code)[0]
        assert error3["code"] == "not_found"
