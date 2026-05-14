from dataclasses import dataclass
from datetime import date, timedelta
from tenancy.models import Tenancy
from common.exceptions import ApartmentOccupiedError, InvalidPeriod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apartments.models import Apartment


def validate_apartment_availability(apartment: "Apartment", start_date: date, end_date: date, exclude_tenancy_id: int | None = None) -> None:
    """
    Validate that the apartment is available for the requested lease period.
    Ensures there is no overlaps.

    :param apartment: Apartment to validate
    :param start_date: Lease start date
    :param end_date: Lease end date
    :param exclude_tenancy_id: Tenancy ID to exclude from overlap check (for updates)
    :raises ApartmentOccupiedError: If apartment has overlapping lease
    """

    overlapping = Tenancy.objects.filter(apartment_id=apartment.pk, start_date__lt=end_date, end_date__gt=start_date)

    if exclude_tenancy_id:
        overlapping = overlapping.exclude(pk=exclude_tenancy_id)

    if overlapping.exists():
        raise ApartmentOccupiedError()

def validate_lease_period(start_date: date, end_date: date) -> None:
    """
    Validate that the lease period is valid (start date before end date and not in the past).

    :param start_date: Lease start date
    :param end_date: Lease end date
    :raises InvalidPeriod: If the lease period is invalid
    """
    if end_date <= start_date or end_date < date.today():
        raise InvalidPeriod()