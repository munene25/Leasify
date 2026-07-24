from unittest.mock import MagicMock
from typing import Any
import pytest
from decimal import Decimal
from rest_framework.exceptions import ValidationError

from tests.types import Factory
from apartments.choices import Block, Wing
from apartments.models import Apartment
from apartments.services import apartment_create, apartment_delete, apartment_update
from tenancy.models import Tenancy


class TestApartmentCreateService:
    """Tests for apartment_create service."""

    def test_apartment_creation(self) -> None:
        """The created apartment should be returned and stored with the supplied values."""

        apartment = apartment_create(
            block=Block.A,
            unit_number=7,
            floor=2,
            rent=Decimal("12000"),
            rentable=True,
            wing=Wing.WEST,
        )
        persisted = Apartment.objects.get(pk=apartment.pk)

        assert apartment == persisted
        assert apartment.block == persisted.block == Block.A
        assert apartment.unit_number == persisted.unit_number == 7
        assert apartment.floor == persisted.floor == 2
        assert apartment.rent == persisted.rent == Decimal("12000")
        assert apartment.rentable == persisted.rentable is True
        assert apartment.wing == persisted.wing == Wing.WEST

    def test_apartment_create_calls_full_clean(self, apartment_data: dict[str, Any], full_clean_patch: MagicMock) -> None:
        """The create service should validate through full_clean."""

        apartment_create(**apartment_data)
        full_clean_patch.assert_called_once()

    def test_apartment_defaults_to_rentable(self, apartment_data: dict[str, Any]) -> None:
        """New apartments should default to rentable."""

        apartment_data.pop("rentable")
        apartment = apartment_create(**apartment_data)
        assert apartment.rentable is True

    def test_apartment_create_query_count(self, apartment_data: dict[str, Any], django_assert_num_queries) -> None:
        """
        1. Validate the apartment data
        2. Insert the apartment record
        """

        with django_assert_num_queries(2):
            apartment_create(**apartment_data)


class TestApartmentUpdateService:
    data = {"block": "OLD", "rent": 10_000, "rentable": True, "unit_number": 2}

    def test_apartment_updates_successfully(self, apartment: Apartment):
        """
        Updated fields should match what is in the db, the returned object and the update data
        """

        updates = self.data
        updated = apartment_update(apartment, **updates)

        apartment.refresh_from_db()  # type: ignore
        assert updated.pk == apartment.pk
        assert updated.rent == apartment.rent == Decimal(updates["rent"])
        assert updated.rentable == apartment.rentable == updates["rentable"]
        assert updated.unit_number == apartment.unit_number == updates["unit_number"]
        assert updated.block == apartment.block == updates["block"]

    def test_apartment_unique_constraints(self, apartment: Apartment):
        """No two apartments should share same block and unit number"""

        apt = apartment_create(**self.data)
        with pytest.raises(ValidationError) as exc:
            apartment_update(apartment=apt, block=apartment.block, unit_number=apartment.unit_number)
        assert "Apartment with this Block and Unit number already exists" in str(exc.value.detail)
        apt.refresh_from_db()  # type: ignore
        assert apt.block == self.data["block"]
        assert apt.unit_number == self.data["unit_number"]
        assert apt.rent == self.data["rent"]
        assert apt.rentable == self.data["rentable"]

    def test_number_of_querries_vary_based_on_the_update_kwargs(self, apartment: Apartment, django_assert_num_queries):
        """
        Apartment should only be updated if fields actually change
        """

        # O querries since no updates are being made
        with django_assert_num_queries(0):
            apartment_update(apartment, block=apartment.block, unit_number=apartment.unit_number)

        # 1 uniqueness check via full clean
        # 1 update
        with django_assert_num_queries(2):
            apartment_update(apartment, **self.data)

        apartment.refresh_from_db()  # type: ignore
        assert apartment.block == self.data["block"]
        assert apartment.unit_number == self.data["unit_number"]
        assert apartment.rent == self.data["rent"]
        assert apartment.rentable == self.data["rentable"]


class TestApartmentDeleteService:

    def test_apartment_deletion_succeeds(self, apartment: Apartment):
        """
        Should delete normally if it's not attached to any tenancy
        """

        apartment_delete(apartment)
        assert Apartment.objects.count() == 0

    def test_deleting_apartment_with_tenant_fails(self, user, apartment: Apartment):
        """
        Should fail to delete and unit should persist
        """
        from tenancy.services import tenancy_create
        from django.utils import timezone

        tenancy_create(user=user, apartment=apartment, start_date=timezone.now().date(), duration_months=2)
        with pytest.raises(ValidationError) as exc:
            apartment_delete(apartment)

        assert "apartment_id" in exc.value.detail
