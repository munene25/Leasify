import pytest
from datetime import date
from functools import partial
from unittest.mock import MagicMock
from rest_framework.exceptions import ValidationError, NotFound
from common.exceptions import MpesaAPIError
from tests.types import Factory, IsClient
from tests.helpers import parse_paginated_response, parse_response, parse_error
from users.models import User
from payments.models import Payment
from payments.choices import PaymentMode as PM, PaymentStatus as PS
from payments.services import payment_mpesa_query, payment_alt_create, payment_mpesa_initiate, payment_mpesa_process
from payments.mpesa import STKResult
from billing.models import BillingPeriod as BP
from billing.choices import BillingStatus as BS
from django.db.models import QuerySet


class TestPaymentListView:
    # authentication and authorization(perms)
    # pagination
    # selector mock - filtering and role based
    # response structure
    path = "/payments/"

    @pytest.mark.parametrize(
        "_client,expected_status",
        [
            ("superuser_client", 200), 
            ("manager_client", 200), 
            ("caretaker_client", 200), 
            ("tenant_client", 200), 
            ("user_client", 403), 
            ("client", 401), 
        ]
    )
    def test_authentication_and_authorization(self, _client: str, expected_status: int, request: pytest.FixtureRequest):
        """Test for auth and permissions, response status varies based on clients"""
        client: IsClient = request.getfixturevalue(_client)
        res = client.get(self.path)
        assert res.status_code == expected_status
    
    def test_pagination(self, payment_factory: Factory[Payment], manager_client: IsClient, override_pagination: int):
        """Should be paginated"""
        payments = payment_factory(3)
        res = parse_paginated_response(manager_client.get(self.path), 3)
        assert len(res["results"]) == override_pagination

    @pytest.mark.parametrize(
        "filters",
        [
            ({"billing": 1}),
            ({"status": PS.PENDING}),
            ({"mode": PM.MPESA}),
            ({"search": "0700"}),
            ({"search": "0700", "status": "pen"}),
        ]
    )
    def test_selector_called_with_correct_args(self, filters: dict, manager_client: IsClient, monkeypatch: pytest.MonkeyPatch):
        """Patch selector and check args"""
        mock = MagicMock(return_value=QuerySet(Payment))
        monkeypatch.setattr("payments.selectors.payment_list_for", mock)
        res = manager_client.get(self.path, filters)
        parse_paginated_response(res, 0)
        mock.assert_called_once_with(
            user=manager_client.user,
            filters=filters
        )

    def test_response_structure(self, payment_factory: Factory[Payment], superuser_client: IsClient):
        """All details and searchable fields should be included"""

        payment = payment_factory(1)[0]
        res = parse_paginated_response(superuser_client.get(self.path), 1)
        results = res["results"][0]
        assert results["payment_id"] == payment.pk
        assert results["billing_id"] == payment.billing_id
        assert results["billing_name"] == payment.billing.name
        assert results["amount"] == str(payment.amount)
        assert results["status"] == payment.status