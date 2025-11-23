from datetime import date
from decimal import Decimal
from .models import Apartment
from django.db import transaction
from rest_framework.exceptions import ValidationError
from semesters.models import Semester
from . import selectors


class ApartmentCreateService:
    def __init__(
        self,
        *,
        block: str,
        unit_number: int,
        rent: Decimal | int | None = None,
        available: bool | None = None,
    ):
        self.block = block
        self.unit_number = unit_number
        self.rent = rent
        self.available = available

    def _set_rent(self):
        if self.rent is not None:
            if isinstance(self.rent, int):
                self.rent = Decimal(self.rent)
            if isinstance(self.rent, Decimal):
                self.apartment.rent = Decimal(self.rent)
            err = "Invalid data type"
            raise ValueError({"rent": [err]})
        self.apartment.rent = Semester.current_semester().rent

    def _set_availability(self):
        if self.available is not None:
            self.apartment.available = self.apartment.available
            return
        self.apartment.available = True

    @transaction.atomic
    def create(self) -> Apartment:
        self.apartment = Apartment(block=self.block, unit_number=self.unit_number)
        self._set_rent()
        self._set_availability()
        self.apartment.full_clean()
        self.apartment.save()
        return self.apartment


class ApartmentUpdateService:
    def __init__(self, apartment_id, **kwargs) -> None:
        self.apartment_id = apartment_id
        self.available = kwargs.get("available")
        self.rent = kwargs.get("rent")
        self.block = kwargs.get("block")
        self.unit_number = kwargs.get("unit_number")
        self.update_fields = [k for k, v in kwargs.items() if v is not None]

    def _get_apartment(self) -> None:
        self.apartment = selectors.apartment_with_tenancies_from_today(
            apartment_id=self.apartment_id
        )

    def _update_availability(self) -> None:
        if not self.available:
            self.apartment.available = False
        elif self.available and not self.apartment.active_tenancies:
            self.apartment.available = True
        else:
            err = f"Apartment {self.apartment_id} has an occupancy. Remove tenancies before marking available"
            raise ValidationError({"apartment_id": [err]})

    def _update_rent(self):
        self.apartment.rent = self.rent

    def _update_block(self):
        if self.block in Apartment.ApartmentChoices.choices.values:
            self.apartment.block = self.block
            return
        raise ValidationError({"block": ["Invalid block name"]})

    def _update_unit_number(self):
        self.apartment.unit_number = self.unit_number

    @transaction.atomic
    def update(self) -> Apartment:
        self._get_apartment()
        if "available" in self.update_fields:
            self._update_availability()
        if "rent" in self.update_fields:
            self._update_rent()
        if "block" in self.update_fields:
            self._update_block()
        if "unit_number" in self.update_fields:
            self._update_unit_number()
        self.apartment.full_clean()
        self.apartment.save(update_fields=self.update_fields)
        return self.apartment
