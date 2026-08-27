from structlog import get_logger
from typing import TypedDict, Unpack, Optional
from decimal import Decimal
from django.db.models import ProtectedError
from rest_framework.exceptions import ValidationError
from leasify.apartments.models import Apartment

from leasify.apartments.choices import Block, Wing

logger = get_logger("apartments.services")


class ApartmentUpdateData(TypedDict, total=False):
    """Represents the typical payload expected for apartment updates."""

    block: Block | str
    unit_number: int
    floor: int
    rent: int | Decimal
    rentable: bool
    wing: Optional[Wing | str]


def apartment_create(*, block: Block, unit_number: int, floor: int, rent: Decimal, wing: Wing | None, rentable: bool = True) -> Apartment:
    """Create a new apartment record.

    Creates and saves a new Apartment instance with the provided parameters.
    Validates the data using full_clean() before saving.

    :param block: The block identifier for the apartment
    :param unit_number: The unit number of the apartment
    :param floor: The floor where the apartment is located
    :param rent: The rent amount for the apartment
    :param wing: The wing identifier for the apartment
    :param rentable: Whether the apartment is rentable (default: True)
    :returns: The created Apartment instance

    :raises ValidationError: If validation fails during full clean
    """
    apartment = Apartment(
        unit_number=unit_number,
        block=block,
        floor=floor,
        wing=wing,
        rent=rent,
        rentable=rentable,
    )
    apartment.full_clean()
    apartment.save()
    logger.info("apartment_created", apartment_id=apartment.pk, apartment_name=str(apartment))
    return apartment


def apartment_update(*, apartment: Apartment, **kwargs: Unpack[ApartmentUpdateData]) -> Apartment:
    """Update an existing apartment.

    Updates the specified fields of an apartment and validates the changes.
    Only updates fields that have changed from their current values.

    :param apartment: The apartment instance to update
    :param kwargs: Dictionary of field names and new values to update
    :returns: The updated Apartment instance

    :raises ValidationError: If validation fails during full clean.
    """
    updates = [k for k, v in kwargs.items() if getattr(apartment, k) != v]
    if not updates:
        return apartment

    for field in updates:
        setattr(apartment, field, kwargs[field])

    apartment.full_clean()
    apartment.save(update_fields=updates)
    logger.info("apartment_updated", apartment_id=apartment.pk, fields=updates)
    return apartment


def apartment_delete(apartment: Apartment) -> None:
    """Delete an apartment record.

    Attempts to delete the apartment. If the apartment is associated with
    any tenancies, raises a ValidationError indicating it cannot be deleted
    without setting the apartment to unrentable first.

    :param apartment: The apartment instance to delete
    :returns: None

    :raises ValidationError: If the apartment is protected by existing tenancies
    """
    try:
        apartment.delete()
    except ProtectedError:
        raise ValidationError({"apartment_id": ["Apartment is already associated with tenancies. Set apartment to unrentable to take it off listings"]})
    logger.warning("apartment_deleted", apartment_id=apartment.pk, apartment_name=str(apartment))