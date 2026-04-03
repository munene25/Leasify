import pytest
from copy import deepcopy
from datetime import timedelta
from freezegun import freeze_time
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.contrib.sessions.backends.cache import SessionStore
from django.core.cache import cache
from rest_framework import status
from users.models import User, Account, EMAIL_COOLDOWN
from tests.types import IsClient, UserCreatePayload
from django.core.mail import EmailMessage
from tests.helpers import parse_error, parse_message, check_links_in_mail

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

    @patch("users.views.user_account_create")
    def test_user_creation_throttles(
        self,
        mock: MagicMock,    
        cache_clear,
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

    def test_user_list_pagination(self, manager_client: IsClient, user_factory,  override_pagination):
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
        pld["phone_number"] = "+254720202202"
        response2 = manager_client.patch(path, pld)
        data2 = parse_message(response2)
        fetched = User.objects.get(pk=user.pk)
        assert fetched.email == data2["email"]
        assert data2["user_id"] == fetched.pk
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

        response5 = user_client.patch(path, {"first_name": "Felix"})
        error5 = parse_error(response5, status_code)[0]
        assert error5["code"] == "permission_denied"

        response5 = user_client.delete(path)
        error5 = parse_error(response5, status_code)[0]
        assert error5["code"] == "permission_denied"

    def test_modifying_priviledged_users_fails(self, manager_client: IsClient, super_user: User):
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
        assert data1["roles"] == []

        updates = {"first_name": "Zane", "email": "testemail1@gmail.com", "phone_number": "+254 710 111 110", "bio": "A regular bio", "roles": ["manager"]}
        response2 = client.patch(self.path, updates)
        data2 = parse_message(response2)
        user.refresh_from_db()
        assert data2.get("user_id", None) is None
        assert data2["first_name"] == updates["first_name"] == user.first_name
        assert data2["phone_number"] == updates["phone_number"].replace(" ", "") == user.account.phone_number
        assert data2["bio"] == updates["bio"] == user.account.bio
        assert data2["email"] != updates["email"] and data2["email"] == user.email
        assert data2["roles"]  != updates["roles"] and data2["roles"] == []
        

        # Unauthorized will be raised
        response3 = client.delete(self.path)
        data = parse_message(response3, status.HTTP_204_NO_CONTENT)
        assert data["message"] == "account deactivated successfully"
        user.refresh_from_db()
        assert user.is_active == False
        response4 = client.get(self.path)
        error =  parse_error(response4, status.HTTP_401_UNAUTHORIZED)[0]
        assert error["code"] == "not_authenticated"

    def test_unauthenticated_requests_fail(self, client: IsClient):
        """
        Should outright deny services for users with"""
        response1 = client.get(self.path)
        error1 = parse_error(response1, status_code=status.HTTP_401_UNAUTHORIZED)[0]
        assert error1["code"] == "not_authenticated"


class TestUserLoginView:
    path = "/users/login"

    def test_user_login_successful(self, user: User, csrf_client: IsClient, password: str):
        """
        Csrf should be explicitly enforced even for unauthenticated users
        last login should be updated.
        A session should be created.
        """
        csrftoken = csrf_client.get("/csrf-token").cookies["csrftoken"].value
        header = {"HTTP_X_CSRFTOKEN" : csrftoken}
        credentials = {"email": user.email, "password": password}

        # -- With csrf tokens  --
        response1 = csrf_client.post(self.path, credentials , **header)
        data1 = parse_message(response1)
        assert data1["email"] == user.email
        user.refresh_from_db()
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
  

        response4 =  client.post(self.path, bad_credentials)
        error4 = parse_error(response4, status.HTTP_429_TOO_MANY_REQUESTS)[0]
        assert error4["code"] == "throttled"

class TestLogoutView:
    path = "/users/logout"
    
    def test_user_logut_successful(self, manager_user: User, client: IsClient, password: str):
        """
        Trying with manager client for variety
        Session should not exist
        Cookie should be unavailable
        Subsequent request should be denied
        """
        session = SessionStore()
        response1 = client.post('/users/login', {"email": manager_user.email, "password": password})
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
    path = "/users/refresh"
    
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
            user.refresh_from_db()
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

            frozen.move_to(timezone.now() + 0.5*EMAIL_COOLDOWN)
            res4 = user_client.post(self.path, self.payload)
            parse_error(res4, status.HTTP_422_UNPROCESSABLE_ENTITY)
            user.refresh_from_db
            assert user.last_email_change == self.before

class TestPasswordChangeView:
    path = "/users/password-change"
    payload = {"password": "Pa55word!", "new_password": "Pa22word!", "confirm_password": "Pa22word!"}
    

    def test_password_change_successfull(self, super_user: User, super_user_client: IsClient, mailoutbox: list[EmailMessage], django_capture_on_commit_callbacks, override_throttles, cache_clear):
        """
            Password should be changed and message in response
            user should be able to login
            session_id should be cycled
        """
        
        session_id1 = super_user_client.post("/users/login", {"email": super_user.email, "password":"Pa55word!"}).cookies["sessionid"].value
        old_password = super_user.password
        
        # -- with correct credentials should evaluate --
        with django_capture_on_commit_callbacks(execute=True):
            res1 = super_user_client.post(self.path, self.payload)
        session_id2 = res1.cookies["sessionid"].value
        data1 = parse_message(res1)
        assert "successfully updated" in data1["message"]
        super_user.refresh_from_db(using=None)
        assert old_password != super_user.password
        assert not super_user.check_password(self.payload["password"])
        assert super_user.check_password(self.payload["new_password"])

        # -- sessionid should be cycled --
        store = SessionStore()
        assert store.exists(session_key=session_id1) == False
        assert store.exists(session_key=session_id2) == True

        # -- mail containing password reset link should be sent --
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [super_user.email]
        assert "password-reset" in mail.body

        # -- subsequent password changes should go through --
        password = self.payload["new_password"]
        res2 = super_user_client.post(self.path, {**self.payload, "password": password})
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
        user.refresh_from_db(None)
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
            errors2 = parse_error(fetch(), status.HTTP_429_TOO_MANY_REQUESTS,)
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
    path = "/users/request/email-verification"

    def test_request_email_verification_successfull(self, user: User, user_client: IsClient, django_capture_on_commit_callbacks, mailoutbox: list[EmailMessage]):
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

    def test_reqest_does_not_send_email_for_verified_user(self, user: User, user_client: IsClient, django_capture_on_commit_callbacks, mailoutbox: list[EmailMessage]):
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

    def test_confirm_email_verification_successful(self, user: User, client: IsClient):
        """
            link in the email can be parsed once it hits the backend.
            email already has been checked for correct tokens and uidb64.
            So in this view i just test the view.
        """

        from users.tokens import uidb64_generate, token_generate

        path = f"/users/confirm/email-verification/{uidb64_generate(user)}/{token_generate(user)}"
        res = client.post(path, {})
        parse_message(res)
        user.refresh_from_db()
        assert user.verified == True

class TestRequestPasswordResetView:
    path = "/users/request/password-reset"

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