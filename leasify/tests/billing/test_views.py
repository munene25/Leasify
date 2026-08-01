import pytest
from unittest.mock import MagicMock
from rest_framework import status
from rest_framework.exceptions import ValidationError
from leasify.tests.types import IsClient, Factory
from leasify.tests.helpers import parse_error, parse_message, parse_paginated_response
from leasify.billing.models import BillingPeriod as BP
from leasify.billing.choices import BillingStatus as BS
from leasify.payments.models import Payment
from datetime import date


class TestBillingListView:
    path = "/billing/"

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
    def test_authentication_and_authorization(self, request: pytest.FixtureRequest, _client: str, expected_status: int, patch_billing_list_for: MagicMock):
        """Test auth and authorization for different client types"""

        client: IsClient = request.getfixturevalue(_client)
        response = client.get(self.path)
        assert response.status_code == expected_status, parse_message(response)

    def test_billing_list_pagination(
        self,
        manager_client: IsClient,
        billing_factory: Factory[BP],
        override_pagination,
    ):
        """Test that list view applies pagination correctly"""
        billing_factory(quantity=5)
        response = manager_client.get(self.path)
        data = parse_paginated_response(response, 5)
        assert len(data["results"]) == 2  # Page size is 2 from override_pagination

    @pytest.mark.parametrize(
        "query_param",
        [
            ({"period_after": date(2026, 1, 1)}),
            ({"period_before": date(2026, 12, 31)}),
            ({"is_current": True}),
            ({"search": "Alex"}),
            ({"period_after": date(2026, 12, 31), "period_after": date(2026, 1, 1)}),
            ({"is_current": False, "search": "Felix"}),
        ],
    )
    def test_billing_list_filters_passed_to_selector(self, query_param: dict, manager_client: IsClient, patch_billing_list_for: MagicMock):
        """Verify filters are validated and passed to selector with correct values"""
        parse_message(manager_client.get(self.path, query_param), 200)
        patch_billing_list_for.assert_called_once_with(user=manager_client.user, filters=query_param)

    def test_filter_validation_fails_on_invalid_params(self, manager_client: IsClient):
        """Test that invalid filters are rejected and valid filters pass"""
        response = manager_client.get(self.path, {"period_after": "2024-invalid"})
        parse_error(response, status_code=status.HTTP_400_BAD_REQUEST, err_type="validation_error")

    def test_billing_list_response_structure(self, manager_client: IsClient, billing_factory: Factory[BP]):
        """Verify response has correct pagination structure with results"""
        billing = billing_factory(quantity=2)

        response = manager_client.get(self.path)
        data = parse_paginated_response(response, 2)
        # start_date ordering
        last_billing = data["results"][0]
        assert last_billing["billing_id"] == billing[1].pk
        assert last_billing["tenancy_id"] == billing[1].tenancy.pk
        assert last_billing["tenant_name"] == billing[1].tenancy.user.full_name
        assert last_billing["status"] == billing[1].status
        assert last_billing["duration_months"] == 1
        assert last_billing["is_current"] == billing[1].is_current


class TestBillingDetailView:
    def path(self, billing_id: int) -> str:
        return f"/billing/{billing_id}"

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
    def test_authentication_and_authorization(self, request: pytest.FixtureRequest, _client: str, expected_status: int, patch_billing_get_for: MagicMock):
        """Test auth and authorization for detail view across different client types"""
        client: IsClient = request.getfixturevalue(_client)
        response = client.get(self.path(1))
        assert response.status_code == expected_status

    def test_billing_detail_selector_called_correctly(self, manager_client: IsClient, patch_billing_get_for: MagicMock):
        """Verify selector is called with correct user and billing_id"""
        manager_client.get(self.path(1))
        patch_billing_get_for.assert_called_once_with(user=manager_client.user, billing_id=1)

    def test_billing_detail_response_structure(self, manager_client: IsClient, billing_factory: Factory[BP]):
        """Verify response has correct billing detail structure"""
        billing = billing_factory()[0]
        response = manager_client.get(self.path(1))
        data = parse_message(response, status.HTTP_200_OK)

        assert data["start_date"] == str(billing.start_date)
        assert data["end_date"] == str(billing.end_date)
        assert data["billing_id"] == billing.pk
        assert data["total_due"] == str(billing.total_due)
        assert data["is_current"] == billing.is_current == True
        assert data["duration_months"] == billing.duration_months


class TestBillingCancelView:
    def path(self, billing_id: int) -> str:
        return f"/billing/{billing_id}/cancel"

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
    def test_authentication_and_authorization(
        self,
        request: pytest.FixtureRequest,
        _client: str,
        expected_status: int,
        monkeypatch: pytest.MonkeyPatch,
        billing_factory: Factory[BP],
    ):
        """Test auth and authorization for cancel view across different client types"""
        billing = billing_factory(quantity=1)[0]
        monkeypatch.setattr("leasify.billing.selectors.billing_get_for", MagicMock(return_value=billing))
        monkeypatch.setattr("leasify.billing.services.billing_period_cancel", MagicMock(return_value=billing))

        client: IsClient = request.getfixturevalue(_client)
        response = client.post(self.path(billing.pk), data={})
        assert response.status_code == expected_status, parse_message(response)
    
    def tests_cancelation_successful(self, manager_client: IsClient, billing_factory: Factory[BP], ):
        """A cancelation request should be successful"""
        billing = billing_factory(statuses=[BS.UNPAID])[0]
        response = manager_client.post(self.path(billing.pk), data={})
        data = parse_message(response)
        assert data["billing_id"] == billing.pk
        assert data["status"] == BS.CANCELLED

    def test_service_and_selector_called_once(self, manager_client: IsClient, billing_factory: Factory[BP], monkeypatch: pytest.MonkeyPatch):
        """Verify selector is called with correct arguments for cancel view"""

        billing = billing_factory(quantity=1)[0]
        mock_service = MagicMock(return_value=billing)
        mock_selector = MagicMock(return_value=billing)
        monkeypatch.setattr("leasify.billing.selectors.billing_get_for", mock_selector)
        monkeypatch.setattr("leasify.billing.services.billing_period_cancel", mock_service)

        manager_client.post(self.path(billing.pk), data={})
        mock_selector.assert_called_once_with(user=manager_client.user, billing_id=billing.pk)
        mock_service.assert_called_once_with(billing)


class TestBillingCompleteView:
    def path(self, billing_id: int) -> str:
        return f"/billing/{billing_id}/complete"

    @pytest.mark.parametrize(
        "_client,expected_status",
        [
            ("superuser_client", 200),
            ("manager_client", 200),
            ("caretaker_client", 403),
            ("tenant_client", 403),
            ("user_client", 403),
            ("client", 401),
        ],
    )
    def test_authentication_and_authorization(
        self,
        request: pytest.FixtureRequest,
        _client: str,
        expected_status: int,
        monkeypatch: pytest.MonkeyPatch,
        billing_factory: Factory[BP],
    ):
        """Test auth and authorization for complete view across different client types"""
        billing = billing_factory(statuses=[BS.UNPAID])[0]
        monkeypatch.setattr("leasify.billing.selectors.billing_get_for", MagicMock(return_value=billing))
        monkeypatch.setattr("leasify.billing.services.billing_period_complete", MagicMock(return_value=billing))

        client: IsClient = request.getfixturevalue(_client)
        response = client.post(self.path(billing.pk), data={})
        assert response.status_code == expected_status, parse_message(response)

    def test_billing_complete_success(self, manager_client: IsClient, billing_factory: Factory[BP], payment_factory: Factory[Payment]):
        """Verify successful complete returns correct response structure"""
        billing = billing_factory(statuses=[BS.UNPAID])[0]
        payment_factory(billing=billing)
        response = manager_client.post(self.path(billing.pk), data={})
        data = parse_message(response, status.HTTP_200_OK)

        assert data["status"] == BS.PAID

    def test_billing_complete_service_and_selector_called_once(self, manager_client: IsClient, billing_factory: Factory[BP], monkeypatch: pytest.MonkeyPatch):
        """Verify selector is called with correct arguments"""
        billing = billing_factory(statuses=[BS.UNPAID])[0]
        mock_selector = MagicMock(return_value=billing)
        mock_service = MagicMock(return_value=billing)
        monkeypatch.setattr("leasify.billing.selectors.billing_get_for", mock_selector)
        monkeypatch.setattr("leasify.billing.services.billing_period_complete", mock_service)

        manager_client.post(self.path(billing.pk), data={})

        mock_service.assert_called_once_with(billing)
        mock_selector.assert_called_once_with(user=manager_client.user, billing_id=billing.pk)

    @pytest.mark.parametrize("billing_status", [BS.PAID, BS.CANCELLED])
    def test_billing_complete_already_paid_or_cancelled(self, manager_client: IsClient, billing_status: BS, billing_factory: Factory[BP],):
        """Test that validation error is raised when billing is already paid or cancelled"""
        billing = billing_factory(statuses=[billing_status])[0]
        response = manager_client.post(self.path(billing.pk), data={})
        errors = parse_error(response, status.HTTP_400_BAD_REQUEST, "validation_error")
        assert billing_status.value in str(errors[0]["detail"])
