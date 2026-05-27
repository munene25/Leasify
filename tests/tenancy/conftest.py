from typing import TYPE_CHECKING
from tenancy.services import tenancy_create
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from datetime import date
    from apartments.models import Apartment
    from users.models import User
    from tenancy.models import Tenancy
    from tests.types import TenancyPayload


@pytest.fixture
def tenancy_payload(user: "User", apartment: "Apartment", today: "date") -> "TenancyPayload":
    return {
        "user": user,
        "apartment": apartment,
        "start_date": today,
        "duration_months": 1
    }

@pytest.fixture
def actual_tenant(tenancy_payload) -> "Tenancy":
    return tenancy_create(**tenancy_payload)

@pytest.fixture
def mock_billing_create(monkeypatch) -> MagicMock:
    """Mock billing period create"""

    mock = MagicMock()
    monkeypatch.setattr("tenancy.services.billing_period_create", mock)
    return mock