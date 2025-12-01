from typing import Any
from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Apartment
from semesters.models import Semester
from . import selectors


class ApartmentService:
    EDITABLE_FIELDS = {"rent", "block", "unit_number", "rentable"}

    def __init__(self, apartment_id: int | None = None):
        self.apartment = (
            selectors.apartment_get_by_id(apartment_id) if apartment_id else None
        )

    def _validate_block(
        self,
        block: str,
    ) -> None:
        errors: dict[str, list[str]] = {}

        # validate block membership
        if block not in Apartment.ApartmentChoices.values:
            errors["block"] = ["Invalid block"]

        if errors:
            raise ValidationError(errors)

    @transaction.atomic
    def create(
        self,
        *,
        block: str,
        unit_number: int,
        rent: Decimal | None = None,
        rentable: bool = True,
    ) -> Apartment:
        # validate first
        self._validate_block(block=block)

        apt = Apartment(
            block=block,
            unit_number=unit_number,
            rent=rent or Semester.current_semester().rent,
            rentable=bool(rentable),
        )
        apt.full_clean()
        apt.save()
        return apt

    @transaction.atomic
    def update(self, **kwargs: dict[str, Any]) -> Apartment:
        if not self.apartment:
            raise ValidationError({"apartment_id": ["Apartment not provided"]})

        # pick only editable and changed fields
        update_fields: dict = {
            k: v
            for k, v in kwargs.items()
            # no FK so this check is valid
            if k in self.EDITABLE_FIELDS and getattr(self.apartment, k) != v
        }
        if "block" in update_fields:
            self._validate_block(update_fields["block"])

        if not update_fields:
            return self.apartment
        
        # Since all editable attributes have no FKs 
        for k, v in update_fields.items():
            setattr(self.apartment, k, v)
        # model validation before saving
        self.apartment.full_clean()
        # save only changed fields
        self.apartment.save(update_fields=list(update_fields.keys()))
        return self.apartment
