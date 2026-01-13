from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Apartment
from .selectors import apartment_for_update


class ApartmentService:
    def __init__(self, apartment_id: int | None = None):
        self.apartment_id = apartment_id
        self.EDITABLE_FIELDS = ("rent", "block", "unit_number", "rentable")

    def _apartment_get_locked(self) -> Apartment:
        if not self.apartment_id:
            raise ValidationError({"apartment_id": ["Apartment not provided"]})
        return apartment_for_update(self.apartment_id)
    
    @transaction.atomic
    def create(
        self,
        *,
        block: str,
        unit_number: int,
        rent: Decimal | int,
        rentable: bool = True,
    ) -> Apartment:
        """
        Create a new apartment, defaults to rentable allowing users to view or book apartment
        
        :param self: ApartmentService instance
        :param block: The block set in apartment choices either "OLD" or "NEW"
        :type block: str
        :param unit_number: The unit_number of the apartment
        :type unit_number: int
        :param rent: the rent charged per semester for the unit/apartment
        :type rent: Decimal | int
        :param rentable: The ability of the apartment to be accessed and viewed by non-admin users and can be booked
        :type rentable: bool
        :return: The created apartment instance
        :rtype: Apartment
        """
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
        params must be in the update fields to be able to execute
        :param self: ApartmentService instance
        :param kwargs: block: str, unit_number: int, rent: Decimal | int, renatble: bool
        :type kwargs: str | int
        :return: Description
        :rtype: Apartment
        """
        apartment = self._apartment_get_locked()

        # pick only editable and changed fields
        update_fields: dict = {
            k: v
            for k, v in kwargs.items()
            if k in self.EDITABLE_FIELDS and getattr(apartment, k) != v
        }
        if not update_fields:
            return apartment
        
        block = update_fields.get("block")
        if block is not None:
            update_fields["block"] = block.uppercase()

        for field, value in update_fields.items():   
            setattr(apartment, field, value)

        apartment.full_clean()
        apartment.save(update_fields=list(update_fields.keys()))
        return apartment

    @transaction.atomic
    def delete(self) -> None:
        """
        Delete an apartment if it has not been associated with a tenancy
        """
        apartment = self._apartment_get_locked()
        if getattr(apartment, "tenancy_set").exists():
            raise ValidationError({"apartment_id": ["Apartment is booked and cannot be deleted"]})
        apartment.delete()