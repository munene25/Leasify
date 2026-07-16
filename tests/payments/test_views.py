import pytest
from datetime import date
from functools import partial
from unittest.mock import MagicMock
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework import status
from common.exceptions import MpesaAPIError
from tests.types import Factory, IsClient
from tests.helpers import parse_paginated_response, parse_message, parse_error
from users.models import User
from payments.models import Payment
from payments.choices import PaymentMode as PM, PaymentStatus as PS
from payments.services import payment_mpesa_query, payment_alt_create, payment_mpesa_initiate, payment_mpesa_process
from payments.mpesa import STKResult
from billing.models import BillingPeriod as BP
from billing.choices import BillingStatus as BS
from django.db.models import QuerySet


class TestPaymentListView:

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
        payment_factory(3)
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

    
class TestPaymentDetailView:

    def path(self, payment_id: int) -> str:
        return f"/payments/{payment_id}/"

    @pytest.mark.parametrize(
        "_client,expected_status",
        [
            ("superuser_client", 200),
            ("manager_client", 200),
            ("caretaker_client", 200),
            ("tenant_client", 200),
            ("user_client", 403),
            ("client", 401),
        ],
    )
    def test_authentication_and_authorization(self, _client: str, expected_status: int, request: pytest.FixtureRequest, patch_payment_get_for: MagicMock):
        """Test auth and authorization for detail view across different client types"""
        client: IsClient = request.getfixturevalue(_client)
        response = client.get(self.path(1))
        assert response.status_code == expected_status

    def test_selector_called_correctly(self, manager_client: IsClient, patch_payment_get_for: MagicMock,):
        """Verify selector is called with correct user and payment_id"""
        manager_client.get(self.path(1))
        patch_payment_get_for.assert_called_once_with(
            user=manager_client.user,
            payment_id=1,
        )

    def test_response_structure(self, superuser_client: IsClient, payment_factory: Factory[Payment]):
        """Verify response has correct payment detail structure"""
        payment = payment_factory(1)[0]
        response = superuser_client.get(self.path(payment.pk))
        data = parse_message(response, status.HTTP_200_OK)

        assert data["payment_id"] == payment.pk
        assert data["billing_id"] == payment.billing_id
        assert data["billing_name"] == payment.billing.name
        assert data["tenant_name"] == payment.billing.tenancy.user.full_name
        assert data["mode"] == payment.mode
        assert data["amount"] == str(payment.amount)
        assert data["status"] == payment.status
        assert data["receipt_no"] == payment.receipt_no
        assert data["phone_number"] == str(payment.phone_number)


class TestPaymentInitiateMpesaView:

    path = "/payments/mpesa/initiate/"

    @pytest.mark.parametrize(
        "_client,expected_status",
        [
            ("superuser_client", 201),
            ("manager_client", 201),
            ("tenant_client", 201),
            ("caretaker", 403),
            ("user_client", 403),
            ("client", 401),
        ],
    )
    def test_authentication_and_authorization(self, _client: str, expected_status: int, request: pytest.FixtureRequest, patch_payment_mpesa_initiate: MagicMock, patch_billing_get_for: MagicMock,):
        """Test auth and authorization for different client types"""
        client: IsClient = request.getfixturevalue(_client)
        response = client.post(self.path, {"billing_id": 1, "phone_number": "254712345678"})
        assert response.status_code == expected_status

    def test_selector_called_correctly(self, manager_client: IsClient, patch_billing_get_for: MagicMock, patch_payment_mpesa_initiate: MagicMock,):
        """Verify billing selector is called with correct args"""
        manager_client.post(self.path, {"billing_id": 1, "phone_number": "254712345678"})
        patch_billing_get_for.assert_called_once_with(
            user=manager_client.user,
            billing_id=1,
        )

    def test_service_called_correctly(self, manager_client: IsClient, patch_billing_get_for: MagicMock, patch_payment_mpesa_initiate: MagicMock,):
        """Verify service is called with correct args"""
        manager_client.post(
            self.path,
            {"billing_id": 1, "phone_number": "254712345678"},
            HTTP_IDEMPOTENCY_KEY="test-idem-key",
        )
        patch_payment_mpesa_initiate.assert_called_once_with(
            billing=patch_billing_get_for.return_value,
            phone_number="254712345678",
            idempotency_key="test-idem-key",
        )

    def test_idempotency_key_optional(self, manager_client: IsClient, patch_billing_get_for: MagicMock, patch_payment_mpesa_initiate: MagicMock,):
        """Verify idempotency key is optional"""
        manager_client.post(self.path, {"billing_id": 1, "phone_number": "254712345678"})
        patch_payment_mpesa_initiate.assert_called_once_with(
            billing=patch_billing_get_for.return_value,
            phone_number="254712345678",
            idempotency_key=None,
        )

    def test_response_structure(self, manager_client: IsClient, patch_billing_get_for: MagicMock, patch_payment_mpesa_initiate: MagicMock,):
        """Verify response structure"""
        response = manager_client.post(self.path, {"billing_id": 1, "phone_number": "254712345678"})
        data = parse_message(response, status.HTTP_201_CREATED)

        assert data["message"] == "M-Pesa transaction initiated."
        assert data["payment_id"] == patch_payment_mpesa_initiate.return_value.pk

    def test_invalid_phone_number(self, manager_client: IsClient, patch_billing_get_for: MagicMock, patch_payment_mpesa_initiate: MagicMock,):
        """Verify invalid phone number returns 400"""
        response = manager_client.post(self.path, {"billing_id": 1, "phone_number": "invalid"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_billing_id(self, manager_client: IsClient, patch_payment_mpesa_initiate: MagicMock,):
        """Verify missing billing_id returns 400"""
        response = manager_client.post(self.path, {"phone_number": "254712345678"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mpesa_api_error(self, manager_client: IsClient, patch_billing_get_for: MagicMock, patch_payment_mpesa_initiate: MagicMock,):
        """Verify MpesaAPIError returns correct status"""
        patch_payment_mpesa_initiate.side_effect = MpesaAPIError("Service unavailable")
        response = manager_client.post(self.path, {"billing_id": 1, "phone_number": "254712345678"})
        assert response.status_code == status.HTTP_424_FAILED_DEPENDENCY