import pytest
from unittest.mock import MagicMock
from decimal import Decimal
from datetime import date
from typing import Any, TYPE_CHECKING
from rest_framework import status
from leasify.apartments.models import Apartment
from leasify.apartments.choices import Block, Wing
from leasify.common.period import DateRange
from leasify.tenancy.models import Tenancy
from leasify.tests.types import IsClient, Factory
from django.urls import reverse
from leasify.tests.helpers import parse_error, parse_message, parse_paginated_response

if TYPE_CHECKING:
    from leasify.users.models import User


class TestApartmentListCreateView:
    path = "/apartments/"
    data = {
        "block": Block.A,
        "unit_number": 1,
        "floor": 0,
        "rent": 10_000,
        "rentable": True,
        "wing": Wing.WEST,
    }

    @pytest.mark.parametrize(
        "_client,get,post",
        [
            ("superuser_client", 200, 201),
            ("manager_client", 200, 201),
            ("caretaker_client", 200, 403),
            ("tenant_client", 200, 403),
            ("user_client", 200, 403),
            ("client", 200, 401),
        ],
    )
    def test_authentication_and_authorization(self, _client: str, get: int, post: int, request: pytest.FixtureRequest):
        """Verify auth and permissions for list and create."""
        client: IsClient = request.getfixturevalue(_client)
        assert client.get(self.path).status_code == get
        assert client.post(self.path, self.data).status_code == post

    def test_create_response_structure(self, manager_client: IsClient):
        """Verify create returns correct structure and persists to DB."""
        response = manager_client.post(self.path, self.data)
        data = parse_message(response, status.HTTP_201_CREATED)
        apartment = Apartment.objects.get(pk=data["apartment_id"])

        assert data["apartment_id"] == apartment.pk
        assert data["block"] == apartment.block == self.data["block"]
        assert data["unit_number"] == apartment.unit_number == self.data["unit_number"]
        assert data["floor"] == apartment.floor == self.data["floor"]
        assert Decimal(data["rent"]) == apartment.rent == self.data["rent"]
        assert data["rentable"] == apartment.rentable == self.data["rentable"]
        assert data["is_occupied"] == False

    def test_list_response_structure(self, manager_client: IsClient, apartment: Apartment):
        """Verify list returns correct structure."""
        response = manager_client.get(self.path)
        data = parse_paginated_response(response, 1)["results"][0]

        assert data["apartment_id"] == apartment.pk
        assert data["name"] == apartment.name
        assert data["floor"] == apartment.floor
        assert data["block"] == apartment.block
        assert data["wing"] == apartment.wing
        assert Decimal(data["rent"]) == apartment.rent
        assert data["is_occupied"] == False

    def test_create_service_called_correctly(self, manager_client: IsClient, monkeypatch: pytest.MonkeyPatch):
        """Verify service is called with correct args including rentable default."""
        mock = MagicMock(return_value=Apartment(pk=1))
        monkeypatch.setattr("leasify.apartments.services.apartment_create", mock)

        data = {k: v for k, v in self.data.items() if k != "rentable"}
        manager_client.post(self.path, data)
        mock.assert_called_once_with(**data, rentable=True)

    @pytest.mark.parametrize(
        "filters",
        [
            {"block": Block.A},
            {"wing": Wing.NORTH},
            {"floor": 1},
            {"unit_number": 10},
            {"rentable": True},
            {"rent_min": 10_000},
            {"rent_max": 20_000},
            {"order_by": "rent"},
            {"order_by": "-rent"},
        ],
    )
    def test_list_selector_called_with_filters(
        self, filters: dict, manager_client: IsClient, monkeypatch: pytest.MonkeyPatch
    ):
        """Verify each filter is passed through to selector."""
        mock = MagicMock(return_value=Apartment.objects.none())
        monkeypatch.setattr("leasify.apartments.selectors.apartment_list_for", mock)
        manager_client.get(self.path, filters)
        mock.assert_called_once_with(user=manager_client.user, filters=filters)

    @pytest.mark.parametrize(
        "field,value",
        [
            ("block", "INVALID"),
            ("unit_number", "five"),
            ("floor", "ground"),
            ("rent", "20 thousand"),
            ("rentable", "okay"),
            ("wing", "INVALID"),
        ],
    )
    def test_create_serializer_validation(self, field: str, value: str, manager_client: IsClient):
        """Verify invalid fields are caught by serializer."""
        response = manager_client.post(self.path, {**self.data, field: value})
        error = parse_error(response, status.HTTP_400_BAD_REQUEST, "validation_error")[0]
        assert error["attr"] == field

    def test_pagination(self, manager_client: IsClient, apartment_factory: Factory[Apartment], override_pagination: int):
        """Verify pagination structure."""
        apartment_factory(quantity=3)
        data = parse_paginated_response(manager_client.get(self.path), 3)
        assert data["previous"] is None
        assert data["next"] is not None
        assert len(data["results"]) == override_pagination


class TestApartmentDetailUpdateDeleteView:

    update_data = {
        "block": Block.B,
        "unit_number": 4,
        "floor": 2,
        "rent": Decimal(30_000),
        "rentable": False,
        "wing": Wing.NORTH,
    }

    @staticmethod
    def path(apartment_id: int) -> str:
        return f"/apartments/{apartment_id}"

    @pytest.mark.parametrize(
        "_client,get,patch,delete",
        [
            ("superuser_client", 200, 200, 204),
            ("manager_client", 200, 200, 204),
            ("caretaker_client", 200, 200, 403),
            ("tenant_client", 403, 403, 403),
            ("user_client", 403, 403, 403),
            ("client", 401, 401, 401),
        ],
    )
    def test_authentication_and_authorization(self, _client: str, get: int, patch: int, delete: int, request: pytest.FixtureRequest, apartment: Apartment):
        """Verify auth and permissions for detail, update and delete."""
        client: IsClient = request.getfixturevalue(_client)
        assert client.get(self.path(apartment.pk)).status_code == get
        assert client.patch(self.path(apartment.pk), self.update_data).status_code == patch
        assert client.delete(self.path(apartment.pk)).status_code == delete

    def test_detail_response_structure(self, manager_client: IsClient, apartment: Apartment):
        """Verify detail returns correct structure with no tenant."""
        response = manager_client.get(self.path(apartment.pk))
        data = parse_message(response, status.HTTP_200_OK)

        assert data["apartment_id"] == apartment.pk
        assert data["block"] == apartment.block
        assert data["unit_number"] == apartment.unit_number
        assert data["floor"] == apartment.floor
        assert Decimal(data["rent"]) == apartment.rent
        assert data["rentable"] == apartment.rentable
        assert data["current_tenant"] is None

    def test_detail_with_active_tenant(self, apartment: Apartment, manager_client: IsClient, tenancy_factory: Factory[Tenancy]):
        """Verify current_tenant is returned when tenancy exists."""
        tenant = tenancy_factory(apartments=[apartment])[0]
        data = parse_message(manager_client.get(self.path(apartment.pk)), status.HTTP_200_OK)
        tenancy_data = data["current_tenant"]
        assert tenancy_data is not None
        assert tenancy_data["tenant_name"] == tenant.user.full_name
        assert tenancy_data["apartment_name"] == tenant.apartment.name
        

    def test_update_service_called_correctly(self, manager_client: IsClient, apartment: Apartment, monkeypatch: pytest.MonkeyPatch):
        """Verify update service is called with correct args."""
        mock = MagicMock(return_value=apartment)
        monkeypatch.setattr("leasify.apartments.services.apartment_update", mock)
        manager_client.patch(self.path(apartment.pk), self.update_data)
        mock.assert_called_once_with(apartment=apartment, **self.update_data)

    def test_update_response_structure(self, manager_client: IsClient, apartment: Apartment):
        """Verify update persists changes and returns correct structure."""
        response = manager_client.patch(self.path(apartment.pk), self.update_data)
        data = parse_message(response, status.HTTP_200_OK)
        apartment.refresh_from_db()

        assert data["apartment_id"] == apartment.pk
        assert data["block"] == apartment.block == self.update_data["block"]
        assert data["floor"] == apartment.floor == self.update_data["floor"]
        assert Decimal(data["rent"]) == apartment.rent == self.update_data["rent"]
        assert data["rentable"] == apartment.rentable == self.update_data["rentable"]

    @pytest.mark.parametrize(
        "field,value",
        [
            ("block", "INVALID"),
            ("unit_number", "five"),
            ("rent", 1_000_000_000),
            ("rentable", "null"),
            ("wing", "INVALID"),
        ],
    )
    def test_update_serializer_validation(self, field: str, value: Any, apartment: Apartment, manager_client: IsClient):
        """Verify invalid fields are caught by serializer."""
        response = manager_client.patch(self.path(apartment.pk), {**self.update_data, field: value})
        error = parse_error(response, status.HTTP_400_BAD_REQUEST, "validation_error")[0]
        assert error["attr"] == field

    def test_delete_service_called_correctly(self, manager_client: IsClient, apartment: Apartment, monkeypatch: pytest.MonkeyPatch):
        """Verify delete service is called with correct apartment."""
        mock = MagicMock()
        monkeypatch.setattr("leasify.apartments.services.apartment_delete", mock)
        manager_client.delete(self.path(apartment.pk))
        mock.assert_called_once_with(apartment)

    @pytest.mark.parametrize("method", ["get", "patch", "delete"])
    def test_not_found(self, manager_client: IsClient, method: str):
        """Returns 404 for non-existent apartment."""
        api = getattr(manager_client, method)
        parse_error(api(self.path(999), {"block": "B"}), status.HTTP_404_NOT_FOUND)


class TestApartmentChoiceView:
    path = "/apartments/choices"

    def test_choices_response_structure(self, client: IsClient):
        """Verify choices endpoint returns block and wing options."""
        data = parse_message(client.get(self.path), status.HTTP_200_OK)

        assert data["block"] == [{"key": k, "display": v} for k, v in Block.choices]
        assert data["wing"] == [{"key": k, "display": v} for k, v in Wing.choices]
