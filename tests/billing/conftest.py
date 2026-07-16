import pytest
from pytest import MonkeyPatch
from unittest.mock import MagicMock
from billing.models import BillingPeriod
from tests.types import Factory
from billing.choices import BillingStatus as BS
from django.db.models import QuerySet


@pytest.fixture()
def patch_billing_list_for(monkeypatch: MonkeyPatch):
    mock = MagicMock(return_value=QuerySet(BillingPeriod))
    monkeypatch.setattr("billing.selectors.billing_list_for", mock)
    yield mock
    
  