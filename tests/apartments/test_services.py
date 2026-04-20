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

    def test_apartment_defaults_to_rentable(self):
        """
        Apartment should by default be rentable
        """
        apartment = apartment_create(block="NEW", unit_number=11, rent=20_000)
        assert apartment.rentable == True

class TestApartmentUpdateService:
    def test_apartment_updates_successfully(self, apartment: Apartment):
        """
        Updated fields should match what is in the db, the returned object and the update data
        """
        
        updates: ApartmentUpdateData  = {"block":"OLD", "rent":10_000, "rentable":True, "unit_number": 2}
        updated = apartment_update(apartment, **updates)

        apartment.refresh_from_db()
        assert updated.pk == apartment.pk
        assert updated.rent == apartment.rent == Decimal(updates["rent"])
        assert updated.rentable == apartment.rentable == updates["rentable"]
        assert updated.unit_number == apartment.unit_number == updates["unit_number"]
        assert updated.block == apartment.block == updates["block"]
