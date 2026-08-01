import pytest
from pytest import MonkeyPatch
from unittest.mock import MagicMock
from leasify.billing.models import BillingPeriod
from leasify.tests.types import Factory
from leasify.billing.choices import BillingStatus as BS
from django.db.models import QuerySet


@pytest.fixture()
def patch_billing_list_for(monkeypatch: MonkeyPatch):
    mock = MagicMock(return_value=QuerySet(BillingPeriod))
    monkeypatch.setattr("billing.selectors.billing_list_for", mock)
    yield mock
    
  