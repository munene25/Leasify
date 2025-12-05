from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Apartment
from .selectors import apartment_for_update


class ApartmentService:
    def __init__(self, apartment_id: int | None = None):
        self.apartment_id = apartment_id
        self.EDITABLE_FIELDS = ("rent", "block", "unit_number", "rentable")

    def _apartment_get_validated(self) -> Apartment:
        if not self.apartment_id:
            raise ValidationError({"apartment_id": ["Apartment not provided"]})
        return apartment_for_update(self.apartment_id)
    
    def _validate_block(self, block: str) -> None:
        if block not in Apartment.ApartmentChoices.values:
            raise ValidationError({"block": ["Invalid block"]})
    
    @transaction.atomic
    def create(
        self,
        *,
        block: str,
        unit_number: int,
        rent: Decimal | int,
        rentable: bool = True,
    ) -> Apartment:
        self._validate_block(block)
        apt = Apartment(
            block=block,
            unit_number=unit_number,
            rent=rent,
            rentable=rentable,
        )
        apt.full_clean()
        apt.save()
        return apt

    @transaction.atomic
    def update(self, **kwargs: str | int) -> Apartment:
        """
        Params: 'rent', 'block', 'unit_number', 'rentable'
        """
        apartment = self._apartment_get_validated()

        # pick only editable and changed fields
        update_fields: dict = {
            k: v
            for k, v in kwargs.items()
            if k in self.EDITABLE_FIELDS and getattr(apartment, k) != v
        }
        if not update_fields:
            return apartment

        if "block" in update_fields:
            self._validate_block(update_fields["block"])

        for k, v in update_fields.items():
            setattr(apartment, k, v)
        apartment.full_clean()
        apartment.save(update_fields=list(update_fields.keys()))
        return apartment

    @transaction.atomic
    def delete(self) -> None:
        apartment = self._apartment_get_validated()
        if getattr(apartment, "tenancy_set").exists():
            raise ValidationError({"apartment_id": ["Apartment is booked and cannot be deleted"]})
        apartment.delete()