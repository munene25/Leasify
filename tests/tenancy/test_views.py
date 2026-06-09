import pytest
from datetime import date
from rest_framework.test import APIClient
from tests.types import IsClient
from tests.types import Factory
from tests.helpers import *
from common.period import today
from tenancy.models import Tenancy
from users.models import User
from tenancy.choices import TenancyStatus as TS, TerminationReason as TR


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
            ("super_user_client", 200, 201),
            ("manager_client", 200, 201),
            ("caretaker_client", 200, 201),
            ("tenant_client", 200, 201),
            ("user_client", 403, 201),
            ("client", 401, 401),
        ],
    )
    def test_authentication_and_authorization(
        self, monkeypatch: pytest.MonkeyPatch, _client: str, get: int, post: int, request: pytest.FixtureRequest
    ):
        """Test both list and create views. Need to patch to speed up."""
        initialized: IsClient = request.getfixturevalue(_client)
        monkeypatch.setattr("tenancy.views.TenancyListCreateView.validate_serializer", lambda *args, **kwargs: {})
        monkeypatch.setattr("tenancy.services.tenancy_create", lambda **kwargs: Tenancy())
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
        
        terminated = tenancy_factory(5, users=users, overrides={"status": TS.TERMINATED})
        defaulting = tenancy_factory(2, users=users[:2], overrides={"status": TS.DEFAULTING})
        active = tenancy_factory(2, users=users[2:4], overrides={"status": TS.ACTIVE})
        
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

        