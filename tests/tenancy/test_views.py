import pytest
from unittest.mock import MagicMock, call
from datetime import date, timedelta
from tests.types import IsClient
from tests.types import Factory
from tests.helpers import *
from common.period import today
from users.models import User
from tenancy.models import Tenancy
from tenancy.choices import TenancyStatus as TS, TerminationReason as TR
from apartments.models import Apartment


class TestTenancyListCreateView:
    path = "/tenancy/"
    data = {
        "apartment": 1,
        "start_date": today(),
        "duration_months": 1,
    }

    @pytest.mark.parametrize(
        "_client,get,post",
        [
            ("superuser_client", 200, 201),
            ("manager_client", 200, 201),
            ("caretaker_client", 200, 201),
            ("tenant_client", 200, 201),
            ("user_client", 403, 201),
            ("client", 401, 401),
        ],
    )
    def test_authentication_and_authorization(
        self,
        monkeypatch: pytest.MonkeyPatch,
        _client: str,
        get: int,
        post: int,
        request: pytest.FixtureRequest,
        mock_serializer,
    ):
        """Test both list and create views. Need to patch to speed up."""
        initialized: IsClient = request.getfixturevalue(_client)
        monkeypatch.setattr("tenancy.views.TenancyListCreateView.validate_serializer", lambda *args, **kwargs: {})
        monkeypatch.setattr("tenancy.services.tenancy_create", lambda **kwargs: Tenancy())
        monkeypatch.setattr("tenancy.serializer.TenancyDetailSerializer", mock_serializer)
        parse_message(initialized.get(self.path), get)
        parse_message(initialized.post(self.path, self.data), post)

    def test_tenancy_list_pagination(
        self, tenancy_factory: Factory[Tenancy], override_pagination, manager_client: IsClient
    ):
        """
        This is as simple as testing pagination occurs
        In the past we have been doing redundant tests on the pagination class itself which is unecessary.
        """

        tenancy_factory(5)
        response = manager_client.get(self.path)
        data = parse_paginated_response(response, 5)
        assert len(data["results"]) == 2

    def test_tenancy_list_filters_based_on_role(
        self,
        caretaker_client: IsClient,
        manager_client: IsClient,
        user_client: IsClient,
        user_factory: Factory[User],
        tenancy_factory: Factory[Tenancy],
        tenancy_patch_validators,
    ):
        users = user_factory(5)

        terminated = tenancy_factory(5, users=users, status=TS.TERMINATED)
        defaulting = tenancy_factory(2, users=users[:2], status=TS.DEFAULTING)
        active = tenancy_factory(2, users=users[2:4], status=TS.ACTIVE)

        res1 = manager_client.get(self.path)
        parse_paginated_response(res1, len(terminated + defaulting + active))

        res2 = caretaker_client.get(self.path)
        parse_paginated_response(res2, len(terminated + active + defaulting))

        # Authenticate on actual tenants
        # users[0] 1 terminated, 1 defaulting
        # users[2] 1 terminated, 1 active
        # users[4] 1 terminated
        user_client.force_authenticate(users[0])
        data1 = parse_paginated_response(user_client.get(self.path), 2)
        assert {t["tenant_name"] for t in data1["results"]} == {users[0].full_name}

        user_client.force_authenticate(users[2])
        data2 = parse_paginated_response(user_client.get(self.path), 2)
        assert {t["tenant_name"] for t in data2["results"]} == {users[2].full_name}

        user_client.force_authenticate(users[4])
        data3 = parse_paginated_response(user_client.get(self.path), 1)
        assert {t["tenant_name"] for t in data3["results"]} == {users[4].full_name}

    @pytest.mark.parametrize(
        "query_param,expected",
        [
            ("joined_after=2026-01-01", {"joined_after": date(2026, 1, 1)}),
            ("joined_before=2026-12-31", {"joined_before": date(2026, 12, 31)}),
            (
                "joined_after=2026-01-01&joined_before=2026-12-31",
                {"joined_after": date(2026, 1, 1), "joined_before": date(2026, 12, 31)},
            ),
            ("search=John", {"search": "John"}),
            ("status=active", {"status": "active"}),
            ("apartment=1", {"apartment": 1}),
        ],
    )
    def test_tenancy_list_query_filters(
        self, monkeypatch, manager_user, manager_client: IsClient, query_param: str, expected: dict[str, Any]
    ):
        """
        Patch list_for and test that filters are called with correct values.
        """
        mock = MagicMock()
        monkeypatch.setattr("tenancy.selectors.tenancy_list_for", mock)

        manager_client.get(self.path + f"?{query_param}")
        mock.assert_called_once_with(user=manager_user, filters=expected)

    def test_tenancy_create_response_format(self, user: User, user_client: IsClient, apartment: Apartment, today):
        """User should be able to create a tenancy and response structure should be correct"""
        response = user_client.post(self.path, data=self.data)
        data = parse_message(response, status_code=201)
        assert Tenancy.objects.count() == 1

        assert data["user_id"] == user.pk
        assert data["apartment_id"] == apartment.pk
        assert data["tenancy_id"] == Tenancy.objects.first().pk  # type: ignore
        assert data["tenant_name"] == user.full_name
        assert data["apartment_name"] == apartment.name
        assert data["status"] == TS.RESERVED
        assert data["paid_up_to"] == None
        assert data["date_joined"] == self.data["start_date"].isoformat()
        assert data["created_at"] is not None
        assert data["termination_reason"] is None
        assert data["termination_date"] is None

    def test_tenancy_create_calls(
        self, monkeypatch, user_client: IsClient, user: User, apartment: Apartment, mock_serializer
    ):
        """Test that tenancy_create is called with correct values"""
        mock = MagicMock(return_value=Tenancy())
        monkeypatch.setattr("tenancy.services.tenancy_create", mock)
        monkeypatch.setattr("tenancy.serializer.TenancyDetailSerializer", mock_serializer)
        user_client.post(self.path, data=self.data)
        mock.assert_called_once_with(
            user=user,
            apartment=apartment,
            start_date=self.data["start_date"],
            duration_months=self.data["duration_months"],
        )


class TestTenancyDetailView:
    def path(self, pk: int):
        return f"/tenancy/{str(pk)}"

    @pytest.mark.parametrize(
        "_client,get",
        [
            ("superuser_client",200,),
            ("manager_client",200,),
            ("caretaker_client",200,),
            ("tenant_client",200,),
            ("user_client",403,),
            ("client",401,),
        ],
    )
    def test_tenancy_detail_auth(self, _client: str, get: int, request, active_tenant: Tenancy):
        """
        Test auth and authorization for different types of clients
        Active tenant is associated with the tenant_client.
        """

        client = request.getfixturevalue(_client)

        parse_message(client.get(self.path(1)), get)

    def test_tenancy_detail_response(self, manager_client: IsClient, active_tenant: Tenancy):
        """Active tenant has a paid period hence last paid"""

        res1 = manager_client.get(self.path(1))
        data1 = parse_message(res1)
        assert data1["user_id"] == active_tenant.user_id
        assert data1["apartment_id"] == active_tenant.apartment.pk
        assert data1["tenancy_id"] == active_tenant.pk
        assert data1["tenant_name"] == active_tenant.user.full_name
        assert data1["apartment_name"] == active_tenant.apartment.name
        assert data1["status"] == active_tenant.status
        assert active_tenant.paid_up_to is not None
        assert data1["paid_up_to"] == active_tenant.paid_up_to.isoformat()
        assert data1["date_joined"] is not None
        assert data1["termination_date"] is None
        assert data1["termination_reason"] is None

    def test_tenancy_detail_response_no_tenancy_found(self, manager_client: IsClient):
        """Test response when no tenancy found for the given pk"""
        res1 = manager_client.get(self.path(99))  # Assuming no tenant with this pk exists
        assert parse_error(res1, 404)


class TestTenancyTerminateView:
    def path(self, pk: int) -> str:
        return f"/tenancy/{str(pk)}/terminate"

    @pytest.mark.parametrize(
        "_client,post",
        [
            ("superuser_client", 200),
            ("manager_client", 200,),
            ("caretaker_client", 200),
            ("tenant_client", 200),
            ("user_client", 403),
            ("client", 401),
        ],
    )
    def test_authentication_and_authorization(self, monkeypatch: pytest.MonkeyPatch, _client: str, post: int, request: pytest.FixtureRequest, mock_serializer):
        """Test both list and create views. Need to patch to avoid validation."""

        client: IsClient = request.getfixturevalue(_client)
        t = Tenancy(status=TS.ACTIVE, user=User())
        monkeypatch.setattr("tenancy.services.tenancy_terminate", lambda *args, **kwargs: t)
        monkeypatch.setattr("tenancy.selectors.tenancy_get_for", lambda *args, **kwargs: t)
        monkeypatch.setattr("tenancy.serializer.TenancyDetailSerializer", mock_serializer)

        parse_message(client.post(self.path(1), {"termination_reason": TR.VOLUNTARY}), post)
    
    def test_filtering_based_on_role(self, monkeypatch, manager_client: IsClient, tenant_client: IsClient, tenancy_factory):
        """Manager client and tenant client should view different tenancies"""

        # create a random tenancy
        t = tenancy_factory()[0]

        # patch to avoid service calls
        monkeypatch.setattr("tenancy.services.tenancy_terminate", lambda *args, **kwargs: t)

        # check that the manager can see it
        parse_message(manager_client.post(self.path(t.id), {"termination_reason": TR.NONPAYMENT}), 200)

        # check that the tenant cannot see it
        parse_message(tenant_client.post(self.path(t.id), {}), 404)

    def test_fails_on_non_existent(self, manager_client: IsClient):
        """Fails on nonexistent tenancy"""
        parse_message(manager_client.post(self.path(999), {}), 404)

    def test_termination_successful(self, manager_client: IsClient, tenancy_factory: Factory[Tenancy], today: date):
        """Manager can set termination reason"""

        t = tenancy_factory()[0]
        tr = {"termination_reason": TR.NONPAYMENT}
        res1 = parse_message(manager_client.post(self.path(t.pk), tr), 200)
        assert res1["status"] == TS.TERMINATED
        assert res1["termination_reason"] == TR.NONPAYMENT
        assert res1["termination_date"] == today.isoformat()

        # test setting of date and reason
        t = tenancy_factory()[0]
        tomorrow = today + timedelta(1)
        res2 = parse_message(manager_client.post(self.path(t.pk), {"termination_date": tomorrow, "termination_reason": TR.MANAGERIAL}), 200)
        assert res2["termination_date"] == tomorrow.isoformat()

    def test_termination_view_calls_terminate_service(self, manager_client, monkeypatch, active_tenant):
        """Termination services should be called once with correct args. This avoids testing service layer in view"""

        tr = {"termination_reason": TR.NONPAYMENT, "termination_date": "2020-12-31"}

        mock = MagicMock(return_value=active_tenant)
        monkeypatch.setattr("tenancy.services.tenancy_terminate", mock)
        parse_message(manager_client.post(self.path(active_tenant.pk), tr), 200)
        mock.assert_called_once_with(
            tenancy=active_tenant,
            termination_reason=tr["termination_reason"],
            termination_date=date.fromisoformat(tr["termination_date"]),
        )


class TestTenancyLeaseExtensionView:
    def path(self, pk):
        return f"/tenancy/{pk}/extend"

    @pytest.mark.parametrize(
        "_client,code",
        [
            ("superuser_client", 200),
            ("manager_client", 200,),
            ("caretaker_client", 200),
            ("tenant_client", 200),
            ("user_client", 403),
            ("client", 401),
        ],
    )
    def test_authentication(self, _client: str, active_tenant: Tenancy, code: int, monkeypatch, request):
        """Test how each client interacts with the view"""
        billing = MagicMock()
        billing.name = "billng"
        billing.pk = 1
        service = MagicMock(return_value=(None, billing))
        monkeypatch.setattr("tenancy.services.tenancy_lease_extend", service)

        url = self.path(active_tenant.pk)
        client = request.getfixturevalue(_client)
        response = client.post(url, data={"duration_months": 2})
        parse_message(response, code)

    def test_calls_service(self, manager_client, monkeypatch, active_tenant):
        """Mock service and assert called with. Avoids multiple repetetive tests"""
        billing = MagicMock()
        billing.name = "billng"
        billing.pk = 1
        service = MagicMock(return_value=(None, billing))
        monkeypatch.setattr("tenancy.services.tenancy_lease_extend", service)

        url = self.path(1)
        manager_client.post(url, data={"duration_months": 2})
        service.assert_called_once_with(tenancy=active_tenant, duration_months=2)

    def test_successful_response_structure(self, tenant_client, active_tenant):
        """Assert returns  the billing name in the response message"""
        url = self.path(1)
        r = tenant_client.post(url, data={"duration_months": 1})
        data = parse_message(r)
        assert str(active_tenant.billings.first()) in data["message"]
        assert active_tenant.billings.first().pk == data["billing_id"]

    def test_unsuccessful_response_structure(self, manager_client):
        """Assert returns the error message"""
        url = self.path(2)
        r = manager_client.post(url, data={"duration_months": 1})
        parse_error(r, 404)[0]


    def test_tenancy_filters_based_on_user(self, manager_client: IsClient, tenant_client: IsClient, caretaker_client: IsClient, monkeypatch):
        """Mock the tenancy_get_for and assert called with correct user"""
        url = self.path(1)
        selector = MagicMock(return_value=Tenancy())
        monkeypatch.setattr("tenancy.selectors.tenancy_get_for", selector)
        service = MagicMock(return_value=(None, "billing"))
        monkeypatch.setattr("tenancy.services.tenancy_lease_extend", service)

        # Assert manager client can access all tenancies
        manager_client.post(url, {})
        caretaker_client.post(url, {})
        tenant_client.post(url, {})
        assert selector.call_args_list == [
            call(manager_client.user, 1),
            call(caretaker_client.user, 1),
            call(tenant_client.user, 1),
        ]


class TestTenancyChoicesViews:
    path = "/tenancy/choices"

    def test_response_structure(self, manager_client: IsClient):
        """Assert all choices are included"""

        response = manager_client.get(self.path)
        data = parse_message(response)
        assert len(data) == 2

        termination_reasons = data["termination_reasons"]
        statuses = data["statuses"]

        assert {"key": TS.DEFAULTING.value, "display": TS.DEFAULTING.label} in statuses
        assert {"key": TR.MANAGERIAL.value, "display": TR.MANAGERIAL.label} in termination_reasons
        assert len(statuses) == len(TS.choices)
        assert len(termination_reasons) == len(TS.choices)

    @pytest.mark.parametrize(
        "_client,code",
        [
            ("superuser_client", 200),
            ("manager_client", 200,),
            ("caretaker_client", 200),
            ("tenant_client", 200),
            ("user_client", 200),
            ("client", 401),
        ],
    )
    def test_auth(self, _client: str, code: int, request):
        """Auth should be as follows"""
        client = request.getfixturevalue(_client)
        response = client.get(self.path)
        assert response.status_code == code
