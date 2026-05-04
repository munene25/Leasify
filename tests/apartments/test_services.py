import pytest
import random
from rest_framework.exceptions import ValidationError
from apartments.services import apartment_create, apartment_delete, apartment_update, ApartmentUpdateData
from apartments.models import Apartment
from decimal import Decimal


class TestApartmentCreateService:
    data = {
            "block": random.choice(Apartment.ApartmentChoices.values),
            "unit_number": 1,
            "rent":15_000,
            "rentable":True
    }

    def test_apartment_creation_successful(self):
        """
        apartment data must match what was input, the db and the returned object
        """

        data = self.data
        apartment = apartment_create(**data)
        fetched = Apartment.objects.first()
        assert fetched is not None
        assert apartment.pk == fetched.pk
        assert apartment.block == data["block"] == fetched.block
        assert apartment.unit_number == data["unit_number"] == fetched.unit_number
        assert apartment.rent == data["rent"] == fetched.rent
        assert apartment.rentable == data["rentable"] == fetched.rentable

    @pytest.mark.parametrize("invalid_block_name", ["new", "New", "old", "OLD "])
    def test_apartment_creation_fails_for_invalid_block(self, invalid_block_name: str):
        """
        apartment block should be only allow those defined in the apartment choices
        """

        data = self.data
        data["block"] = invalid_block_name

        with pytest.raises(ValidationError) as exc:
            apartment_create(**data)

        assert "block" in exc.value.detail

    def test_apartment_unique_constraints(self, apartment: Apartment):
        """
        No two apartments can have the same block and unit_number
        """

        with pytest.raises(ValidationError) as exc:
            apartment_create(block=apartment.block, unit_number=apartment.unit_number, rent=apartment.rent)
        assert "Apartment with this Block and Unit number already exists" in str(exc.value.detail)
        assert Apartment.objects.count() == 1

    def test_apartment_defaults_to_rentable(self):
        """
        Apartment should by default be rentable
        """
        apartment = apartment_create(block="NEW", unit_number=11, rent=20_000)
        assert apartment.rentable == True


class TestApartmentUpdateService:
    data = {"block": "OLD", "rent": 10_000, "rentable": True, "unit_number": 2}

    def test_apartment_updates_successfully(self, apartment: Apartment):
        """
        Updated fields should match what is in the db, the returned object and the update data
        """

        updates = self.data
        updated = apartment_update(apartment, **updates)

        apartment.refresh_from_db() #type: ignore
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
        apt.refresh_from_db() #type: ignore
        assert apt.block == self.data["block"]
        assert apt.unit_number == self.data["unit_number"]
        assert apt.rent == self.data["rent"]
        assert apt.rentable == self.data["rentable"]

    def test_number_of_querries_vary_based_on_the_update_kwargs(self, apartment: Apartment, django_assert_num_queries):
        """
        Apartment should only be updated if fields actually change
        """

        # Should always include the transactions
        with django_assert_num_queries(2):
            apartment_update(apartment, block=apartment.block, unit_number=apartment.unit_number)

        # 2 transaction querries
        # 1 uniqueness check via full clean
        # 1 update
        with django_assert_num_queries(4):
            apartment_update(apartment, **self.data)

        apartment.refresh_from_db() #type: ignore
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

    def test_apartment_with_tenant_fails(self, user, apartment: Apartment):
        """
        Should fail to delete and unit should persist
        """
        from tenancy.models import Tenancy
        from semesters.models import Semester
        from datetime import date

        # create sem
        s = Semester.objects.create(start_date=date(2025, 1, 1), end_date=date(2025, 5, 31), off_season=True)
        # create tenant
        Tenancy.objects.create(user=user, semester=s, apartment=apartment, total_paid=Decimal(0))

        with pytest.raises(ValidationError) as exc:
            apartment_delete(apartment)

        assert "apartment_id" in exc.value.detail
