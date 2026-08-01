from unittest.mock import MagicMock
from typing import Any
import pytest
from decimal import Decimal
from rest_framework.exceptions import ValidationError

from leasify.tests.types import Factory
from leasify.apartments.choices import Block, Wing
from leasify.apartments.models import Apartment
from leasify.apartments.services import apartment_create, apartment_delete, apartment_update
from leasify.tenancy.models import Tenancy


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
    """Tests for apartment_update service."""

    def test_updating_successful(self, apartment: Apartment) -> None:
        """The update service should return the same apartment instance and persist changes."""
        updated = apartment_update(
            apartment=apartment,
            block=Block.B,
            rent=Decimal("15000"),
            rentable=False,
            floor=10,
            wing=Wing.SOUTH
        )

        apartment.refresh_from_db()  # type: ignore

        assert updated == apartment
        assert updated.pk == apartment.pk
        assert apartment.block == Block.B
        assert apartment.rent == Decimal("15000")
        assert apartment.rentable is False
        assert apartment.floor == 10
        assert apartment.wing == Wing.SOUTH

    def test_apartment_update_calls_full_clean(self, apartment: Apartment, full_clean_patch: MagicMock) -> None:
        """The update service should validate through full_clean."""

        apartment_update(apartment=apartment, block=Block.B, rent=Decimal("15000"), rentable=False)
        full_clean_patch.assert_called_once()

    def test_update_query_count(self, apartment: Apartment, django_assert_num_queries) -> None:
        """
        1. No-op update should do no DB writes
        2. A real update should validate and save changes
        """
        with django_assert_num_queries(0):
            apartment_update(
                apartment=apartment,
                block=apartment.block,
                unit_number=apartment.unit_number,
                floor=apartment.floor,
                rent=apartment.rent,
                rentable=apartment.rentable,
                wing=apartment.wing,
            )

        with django_assert_num_queries(2):
            apartment_update(apartment=apartment, block=Block.B, rent=Decimal("15000"), rentable=False)


class TestApartmentDeleteService:
    """Tests for apartment_delete service."""

    def test_apartment_deletion_succeeds(self, apartment: Apartment) -> None:
        """An apartment without dependents should delete normally."""
        apartment_delete(apartment)
        assert Apartment.objects.filter(pk=apartment.pk).exists() is False

    def test_deleting_apartment_with_tenant_fails(self, apartment: Apartment, tenancy_factory: Factory[Tenancy]) -> None:
        """Deleting an apartment with a tenancy should raise a validation error."""
        tenancy_factory(apartments=[apartment])
        with pytest.raises(ValidationError) as exc:
            apartment_delete(apartment)

        assert "apartment_id" in exc.value.detail
        assert Apartment.objects.filter(pk=apartment.pk).exists() is True
