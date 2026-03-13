import pytest
from rest_framework import status
from users.models import User, Account
from unittest.mock import patch, MagicMock
from copy import deepcopy
from django.core.cache import cache
from tests.types import IsClient, UserCreatePayload


@pytest.fixture(autouse=True)
def auto_clear(cache_clear):
    pass

class TestUserListCreateView:
    path = "/users/"

    def test_post_creates_a_user(
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
    def test_creating_user_fails_for_db_constraints(self, field: str, value: str, client: IsClient):
        """
        Similar email and phone number should raise 400
        """
        defaults = {"first_name": "test", "last_name": "test", "password": "Pa55word!", "notify": False}
        payload1 = {**defaults, "phone_number": "0710 100 100", "email": "test1@gmail.com"}
        payload2 = {**defaults, "phone_number": "0720 200 200", "email": "test2@gmail.com"}

        payload1[field] = payload2[field] = value
        client.post(self.path, payload1)

        response2 = client.post(self.path, payload2)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        err_type = response2.data["type"]
        errors = response2.data["errors"][0]
        assert err_type == "validation_error"
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
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        err_type = response.data["type"]
        errors = response.data["errors"][0]
        assert err_type == "validation_error"
        assert errors["code"] == "invalid"
        assert errors["attr"] == "phone_number"

        # -- Fails for a short names, both fields should appear in the error dict --
        payload2 = deepcopy(user_create_payload)
        payload2["first_name"] = "F"
        payload2["last_name"] = "F"

        response2 = client.post(self.path, payload2)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

        # assert structre, should have two error messages
        err_type = response2.data["type"]
        errors = response2.data["errors"]
        # Two fields were input incorrectly hence 2 errors
        assert len(errors) == 2
        assert err_type == "validation_error"
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
        assert response2.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert mock.call_count == 1

        # test structure of the response
        err_type = response2.data["type"]
        errors = response2.data["errors"][0]
        assert err_type == "client_error"
        assert errors["code"] == "throttled"

        # -- With third request should succeed after clearing cache
        cache.clear()
        response3 = client.post(self.path, user_create_payload)

        assert response3.status_code == status.HTTP_201_CREATED
        assert mock.call_count == 2

    def test_get_user_list_authentication_authorization(
        self, client: IsClient, manager_client: IsClient, tenant_client: IsClient
    ):
        """
        No authentication class on the view
        Authentication is handled after the view instantiates
        Permission denied: Unauthorized users |  Unauthorized: unauthenticated users
        """

        # -- with unauthenticated user should raise Unauthorized --
        response = client.get(self.path)
        # Unauthorized will first be raised
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # test repsonse structure
        err_type = response.data["type"]
        errors = response.data["errors"][0]
        assert err_type == "client_error"
        assert errors["code"] == "not_authenticated"

        # -- with an authenticated but unauthorized user should raise 403 --
        response2 = tenant_client.get(self.path)
        assert response2.status_code == status.HTTP_403_FORBIDDEN

        # test response structure
        err_type = response2.data["type"]
        errors = response2.data["errors"][0]
        assert err_type == "client_error"
        assert errors["code"] == "permission_denied"

        # -- with an authorized user with sufficient permission should pass --
        response3 = manager_client.get(self.path)
        assert response3.status_code == status.HTTP_200_OK

    def test_get_user_list_pagination(self, user_factory, manager_client: IsClient, override_pagination):
        """
        Test the pagination structure and data
        Order is reversed so the first user appears in the last index
        I used a serializer to validate the fields
        """
        from users.serializer import UserListSerializer

        total_users = 3
        base_url = "http://testserver/users/"

        users: list[User] = user_factory(total_users - 1)
        first_user = users[total_users - 2]

        response1 = manager_client.get(self.path)

        assert response1.status_code == status.HTTP_200_OK
        assert response1.data is not None and isinstance(response1.data, dict)

        count1 = response1.data["count"]
        next1 = response1.data["next"]
        previous1 = response1.data["previous"]
        results1 = response1.data["results"]

        # The manager client has created a new user in the db
        assert count1 == total_users

        assert next1 == f"{base_url}?page=2"
        assert previous1 == None
        assert len(results1) == override_pagination

        data1 = results1[0]
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

    def test_user_list_filters(self, user_factory, caretaker_client: IsClient):
        """
        Test the new search field implementation
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

        # -- with id filter
        data1 = fetch("id=4")
        assert len(data1) == 1
        fetched = User.objects.get(pk=4)
        assert data1[0]["user_id"] == 4
        assert fetched.email == data1[0]["email"]

        # -- with is_active filter --
        data2 = fetch("is_active=false")
        assert len(data2) == 1
        assert data2[0]["email"] == user5.email
        
        # -- with name search filtering
        sliced_name = user1.get_full_name()[:4]
        data3 = fetch(f"search={sliced_name}")
        assert len(data3) >= 1
        assert user1.pk in [user["user_id"] for user in data3]

        # -- with phone_number search filtering
        sliced_phone = str(user3.account.phone_number)[:5]
        data4 = fetch(f"search={sliced_phone}")
        assert len(data4) >= 1
        assert user3.pk in [user["user_id"] for user in data4]
 
        # -- with exact fields (email) search filtering
        data5 = fetch(f"search={user3.email}")
        assert len(data5) == 1
        assert user3.email == data5[0]["email"]

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


class TestUserDetailUpdateDestroyView:
    path: str = "/users/"

    def test_user_detail_succeeds(self, user_create_payload, user: User, manager_client: IsClient):
        """
        test for get, patch and delete routes success in one place
        """
        def get_message(response) -> dict[str, str]:
            """helper function """
            assert response.status_code == status.HTTP_200_OK
            return response.data
        
        # -- Test get data is accurate --
        pld = user_create_payload
        path = self.path + str(user.pk)
        response1 = manager_client.get(path)
        data1 = get_message(response1)
        assert data1["email"] == user.email
        assert data1["first_name"] == user.first_name
        assert data1["last_name"] == user.last_name
        assert data1["bio"] == user.account.bio
        assert data1["phone_number"] == str(user.account.phone_number)
        
        # -- Test patching data succeds --
        pld["phone_number"] = "+254720202202"
        response2 = manager_client.patch(path, pld)
        data2 = get_message(response2)
        fetched = User.objects.get(pk=user.pk)
        assert fetched.email == data2["email"]
        assert data2["phone_number"] == str(fetched.account.phone_number) == pld["phone_number"]
        assert data2["first_name"] == fetched.first_name == pld["first_name"]
        assert data2["last_name"] == fetched.last_name == pld["last_name"]
        
        reponse3 = manager_client.delete(path)
        data3 = get_message(reponse3)
        fetched2 = User.objects.get(pk=user.pk)
        assert fetched2.is_active == False

    def test_user_detail_view_authentication(self, user_client, caretaker_client):
        pass