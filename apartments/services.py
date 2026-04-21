from structlog import get_logger
from typing import TypedDict, Unpack
from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError
from apartments.models import Apartment

logger = get_logger("apartments.services")

class ApartmentUpdateData(TypedDict, total=False):
    """Represents the payload expected for the user_update function"""

    block: str
    unit_number: int
    rent: int | Decimal
    rentable: bool

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

    apartment = Apartment(
        block=block,
        unit_number=unit_number,
        rent=rent,
        rentable=rentable,
    )
    apartment.full_clean()
    apartment.save()
    logger.info(f"apartment {str(apartment)} created")
    return apartment

@transaction.atomic
def apartment_update(apartment: Apartment, **kwargs: Unpack[ApartmentUpdateData]) -> Apartment:
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
    logger.info(f"apartment {str(apartment)} updated. [data: {update_fields}]")
    return apartment

def apartment_delete(apartment: Apartment) -> None:
    """
    Delete an apartment if it has not been associated with a tenancy.
    """
    if getattr(apartment, "tenancy_set").exists():
        raise ValidationError({"apartment_id": ["Apartment is booked and cannot be deleted"]})
    apartment.delete()
    logger.warning(f"apartment {str(apartment)} deleted")