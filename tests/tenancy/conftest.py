import pytest
from typing import TYPE_CHECKING
from rest_framework.test import APIClient
from unittest.mock import MagicMock
from tenancy.choices import TenancyStatus as TS
from billing.choices import BillingStatus as BS
from common.period import DateRange

if TYPE_CHECKING:
    from datetime import date
    from apartments.models import Apartment
    from users.models import User
    from tenancy.models import Tenancy
    from tests.types import TenancyPayload
    from billing.models import BillingPeriod as BP
    from tests.types import Factory


@pytest.fixture
def tenancy_payload(user: "User", apartment: "Apartment", today: "date") -> "TenancyPayload":
    return {
        "user": user,
        "apartment": apartment,
        "start_date": today,
        "duration_months": 1
    }

@pytest.fixture
def tenant_client(active_tenant: "Tenancy") -> APIClient:
    client = APIClient()
    client.force_authenticate(user=active_tenant.user)
    setattr(client, "user", active_tenant.user)
    return client

@pytest.fixture
def reserved_tenant(tenancy_factory, billing_factory: "Factory[BP]") -> "Tenancy":
    t = tenancy_factory(status=TS.RESERVED)[0]
    starting = DateRange.for_month().previous_month().start_date
    billing_factory(tenancy=t, statuses=[BS.UNPAID], starting=starting)
    return t


@pytest.fixture
def active_tenant(tenancy_factory: "Factory[Tenancy]", billing_factory: "Factory[BP]") -> "Tenancy":
    t = tenancy_factory(status=TS.ACTIVE)[0]
    billing_factory(tenancy=t, statuses=[BS.PAID],)
    return t
    
@pytest.fixture
def mock_billing_create(monkeypatch) -> MagicMock:
    """Mock billing period create"""

    mock = MagicMock()
    monkeypatch.setattr("tenancy.services.billing_period_create", mock)
    return mock