from typing import TYPE_CHECKING
from decimal import Decimal
from structlog import get_logger
from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from tenancy.models import Tenancy, MOVING_WINDOW, DEFAULT_RESERVATION_DURATION
from tenancy.validators import validate_lease_period, validate_max_number_of_reservations
from common.period import DateRange
from django.contrib.auth.models import Group
from users.services import user_set_role
from apartments.selectors import apartment_lock

logger = get_logger("tenancy.services")

if TYPE_CHECKING:
    from users.models import User
    from apartments.models import Apartment


@transaction.atomic
def tenancy_create(
    *,
    user: "User",
    apartment: "Apartment",
    start_date: date,
    duration_months: int,
    reservation_duration: timedelta = DEFAULT_RESERVATION_DURATION,
    status: Tenancy.Status = Tenancy.Status.PENDING,
    rent_snapshot: Decimal | None = None,
) -> Tenancy:
    """
    Create a tenancy record for a user, apartment, and lease period.
    Add user to tenant group.

    :param user: The tenant user
    :param apartment: The apartment to be rented
    :param start_date: Lease start date
    :param duration_months: Lease duration in months
    :param reservation_duration: The duration for which the reservation is valid before it expires
    :param status: The initial status of the tenancy
    :param total_due: The total amount due for the tenancy. If not provided, it will be calculated based on the apartment rent and lease duration.
    :return: The created tenancy record
    """

    # Immediately check if the user has exceeded the maximum number of reservations before doing any further processing.
    validate_max_number_of_reservations(user.pk)

    # lock the apartment record to prevent race conditions.
    # This is required as there really is no db constraint that can prevent overlapping tenancies for the same apartment.
    apartment = apartment_lock(apartment.pk)

    # Normalize start dates to quantize the lease periods into whole months.
    r = DateRange.compute_lease_window(start_date, duration_months)

    # Validate the lease period and apartment availability before creating the tenancy record.
    validate_lease_period(apartment_id=apartment.pk, date_range=r)

    tenancy = Tenancy(
        user=user,
        apartment=apartment,
        start_date=r.start_date,
        end_date=r.end_date,
        rent_snapshot=rent_snapshot or apartment.rent,
        status=status,
        reservation_expiration=r.start_date + reservation_duration,
    )

    tenancy.full_clean()
    tenancy.save()

    # Add user to Tenant group if not already
    if not user.groups.filter(name="tenant").exists():
        user_set_role(user=user, role=Group.objects.get(name="tenant"))

    logger.info(
        "tenancy_created",
        tenancy_id=tenancy.pk,
        tenant_name=user.full_name,
        end_date=r.end_date,
        start_date=r.start_date,
        duration_months=duration_months,
        apartment=str(apartment),
        status=tenancy.status,
    )
    return tenancy


@transaction.atomic
def tenancy_update(
    tenancy: Tenancy, lease_extension_months: int | None = None, apartment: "Apartment | None" = None
) -> Tenancy:
    """
    Provide means for tenants to extend their lease or switch apartment.

    :param tenancy: The tenancy record to be updated
    :param lease_extension_months: The amount of time in months to extend the lease
    :param apartment: The new apartment to be assigned.
    :return: The updated tenancy record
    """

    update_fields: list[str] = []
    r = DateRange(tenancy.start_date, tenancy.end_date)
    if apartment and apartment != tenancy.apartment:
        apartment_obj = apartment_lock(apartment.pk)
        moving_window = tenancy.start_date + MOVING_WINDOW
        if timezone.now().date() >= moving_window:
            raise ValidationError(f"Apartment can only be changed {MOVING_WINDOW.days} days into the lease.")

        tenancy.apartment = apartment_obj
        update_fields.append("apartment")
    else:
        apartment_obj = tenancy.apartment

    if lease_extension_months:
        r = r.shift_months(0, lease_extension_months)
        # No need to validate preiod validity as the extension can only be positive and we assume the existing end_date is valid.
        tenancy.end_date = r.end_date
        update_fields.append("end_date")


    # short circuit if there are no changes to be made
    if not update_fields:
        return tenancy

    validate_lease_period(apartment_id=apartment_obj.pk, date_range=r, exclude_tenancy_id=tenancy.pk)
    tenancy.full_clean()
    tenancy.save(update_fields=update_fields)
    logger.info("tenancy_updated", tenancy_id=tenancy.pk, fields=update_fields)
    return tenancy


@transaction.atomic
def tenancy_extend_reservation(tenancy: Tenancy, reservation_extension: timedelta) -> Tenancy:
    """
    Means for admins to increase select tenants reservation time as they wait for tenant to clear payment.

    :param: tenancy: Tenancy being updated.
    :param: reservation_extension: The range of time to extend the expiration.
    :return: Updated tenancy record.
    """

    tenancy.reservation_expiration += reservation_extension
    tenancy.full_clean()
    tenancy.save(update_fields=["reservation_expiration"])
    logger.info("tenancy_reservation_extended", duration_days=reservation_extension.days)
    return tenancy


@transaction.atomic
def tenancy_terminate(tenancy: Tenancy, termination_date: date | None = None) -> None:
    """
    Delete tenant record and credit all the payments.
    Change to expired and set end date.
    
    :param termination_date: The date the tenancy ends, defaults to today's date.
    :param tenancy: The tenancy instance to terminate.
    :return: None
    """

    tenancy.status = Tenancy.Status.TERMINATED
    tenancy.end_date = termination_date or timezone.now().date()
    tenancy.save(update_fields=["status", "end_date"])

    logger.info(
        "tenancy_terminated",
        tenancy_id=tenancy.pk,
        terminated_at=str(termination_date)
    )