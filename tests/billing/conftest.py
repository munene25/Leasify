import pytest
from pytest import MonkeyPatch
from unittest.mock import MagicMock
from billing.models import BillingPeriod
from tests.types import Factory
from billing.choices import BillingStatus as BS
from django.db.models import QuerySet




@pytest.fixture()
def patch_billing_get_for(monkeypatch: MonkeyPatch, billing_factory: Factory[BillingPeriod]):
    billing = billing_factory(1, statuses=[BS.UNPAID])[0]
    mock = MagicMock(return_value=billing)
    monkeypatch.setattr("billing.selectors.billing_get_for", mock)
    yield mock

@pytest.fixture()
def patch_billing_list_for(monkeypatch: MonkeyPatch):
    mock = MagicMock(return_value=QuerySet(BillingPeriod))
    monkeypatch.setattr("billing.selectors.billing_list_for", mock)
    yield mock
    
  