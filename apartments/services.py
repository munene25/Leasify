from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Apartment

@transaction.atomic
def apartment_create(*, block: str, unit_number: int, rent: Decimal | int, rentable: bool = True) -> Apartment:
    """
    Create an apartment with the given details.

    :param block: Apartment block, must be uppercase letters only
    :type block: str

    :param unit_number: Apartment unit number
    :type unit_number: int

    :param rent: Apartment rent
    :type rent: Decimal or int

    :param rentable: Apartment rentable status, defaults to True
    :type rentable: bool
    
    :return: created Apartment instance
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
def apartment_update(apartment: Apartment, **kwargs: str | int) -> Apartment:
    """
    Update apartment fields.
    
    :param apartment: Apartment instance to update
    :type apartment: Apartment

    :param kwargs: fields to update with their new values
        block: (str) Apartment block, must be uppercase letters only
        unit_number: (int) Apartment unit number 
        rent: (Decimal or int) Apartment rent
        rentable: (bool) Apartment rentable status

    :return: updated Apartment instance
    "rtype: Apartment
    """
    editable_fields = {"rent", "block", "unit_number", "rentable"}
    update_fields: dict= {
        k: v for k, v in kwargs.items() if k in editable_fields and getattr(apartment, k) != v
    }
    if not update_fields:
        return apartment
    
    for field, value in update_fields.items():
        setattr(apartment, field, value)

    apartment.full_clean()
    apartment.save(update_fields=list(update_fields.keys()))
    return apartment

def apartment_delete(apartment: Apartment) -> None:
    """
    Delete an apartment if it has not been associated with a tenancy
    """
    if getattr(apartment, "tenancy_set").exists():
        raise ValidationError({"apartment_id": ["Apartment is booked and cannot be deleted"]})
    apartment.delete()