import pytest
from unittest.mock import MagicMock
from datetime import date
from tests.types import IsClient
from tests.types import Factory
from tests.helpers import *
from common.period import today
from tenancy.models import Tenancy
from users.models import User
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
        self, monkeypatch: pytest.MonkeyPatch, _client: str, get: int, post: int, request: pytest.FixtureRequest, mock_serializer,
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
        assert data["apartment_name"] == apartment.apartment_name
        assert data["status"] == TS.RESERVED
        assert data["paid_up_to"] == None
        assert data["date_joined"] == self.data["start_date"].isoformat()
        assert data["created_at"] is not None
        assert data["termination_reason"] is None
        assert data["termination_date"] is None

    def test_tenancy_create_calls(self, monkeypatch, user_client: IsClient, user: User, apartment: Apartment, mock_serializer):
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
        assert data1["apartment_name"] == active_tenant.apartment.apartment_name
        assert data1["status"] == active_tenant.status
        assert active_tenant.paid_up_to is not None
        assert data1["paid_up_to"] == active_tenant.paid_up_to.isoformat()
        assert data1["date_joined"] is not None
        assert data1["termination_date"] is None
        assert data1["termination_reason"] is None
