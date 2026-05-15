from typing import TYPE_CHECKING
from decimal import Decimal
from structlog import get_logger
from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from tenancy.models import Tenancy, MOVING_WINDOW, DEFAULT_RESERVATION_DURATION
from tenancy.selectors import tenancy_lock
from tenancy.validators import validate_lease_period, validate_max_number_of_reservations
from payments.services import PaymentCreateService
from django.contrib.auth.models import Group
from users.services import user_set_role
from apartments.selectors import apartment_lock

logger = get_logger("tenancy.services")

if TYPE_CHECKING:
    from users.models import User
    from apartments.models import Apartment
    from payments.models import Payment


@transaction.atomic
def tenancy_create(
    *,
    user: "User",
    apartment: "Apartment",
    start_date: date,
    duration_months: int,
    reservation_duration: timedelta = DEFAULT_RESERVATION_DURATION,
    status: Tenancy.TenancyStatus = Tenancy.TenancyStatus.PENDING,
    total_due: Decimal | None = None,
) -> Tenancy:
    """
    Create a tenancy record for a user, apartment, and lease period.
    Add user to tenant group.

    :param user: The tenant user
    :param apartment: The apartment to be rented
    :param start_date: Lease start date
    :param duration_months: Lease duration in months
    :param total_paid: The total amount paid by the tenant at the time of tenancy creation
    :param reservation_duration: The duration for which the reservation is valid before it expires
    :param status: The initial status of the tenancy
    :param total_due: The total amount due for the tenancy. If not provided, it will be calculated based on the apartment rent and lease duration.
    :return: The created tenancy record
    """
    from django.utils import timezone

    # Immediately check if the user has exceeded the maximum number of reservations before doing any further processing.
    validate_max_number_of_reservations(user.pk)

    # lock the apartment record to prevent race conditions.
    # This is required as there really is no db constraint that can prevent overlapping tenancies for the same apartment.
    apartment = apartment_lock(apartment.pk)

    # Normalize start dates to quantize the lease periods into whole months.
    normalized_start_date, normalized_end_date = normalize_lease_period(start_date, duration_months)

    # Validate the lease period and apartment availability before creating the tenancy record.
    validate_lease_period(apartment.pk, normalized_start_date, normalized_end_date)

    # calculate total due if not provided.
    total_due = total_due or (apartment.rent * duration_months).quantize(Decimal("0.01"))

    tenancy = Tenancy(
        user=user,
        apartment=apartment,
        start_date=normalized_start_date,
        end_date=normalized_end_date,
        total_due=total_due,
        status=status,
        reservation_expiration=timezone.now().date() + reservation_duration,
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
        start_date=normalized_start_date,
        end_date=normalized_end_date,
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
    :param extension: The amount of time to extend the lease (only for tenants)
    :param apartment: The new apartment to be assigned (only for admins)
    :return: The updated tenancy record
    """

    update_fields = []
    if apartment and apartment != tenancy.apartment:

        apartment = apartment_lock(apartment.pk)

        moving_window = tenancy.start_date + MOVING_WINDOW
        if timezone.now().date() >= moving_window:
            raise ValidationError(f"Apartment can only be changed {MOVING_WINDOW.days} days into the lease.")

        tenancy.apartment = apartment
        update_fields.append("apartment")
    else:
        apartment = tenancy.apartment

    if lease_extension_months:
        from calendar import monthrange

        end_date = tenancy.end_date + timedelta(days=lease_extension_months * 30)
        end_month_last_day = monthrange(end_date.year, end_date.month)[1]
        end_date = end_date.replace(day=end_month_last_day)

        # No need to validate preiod validity as the extension can only be positive and we assume the existing end_date is valid.
        tenancy.end_date = end_date
        update_fields.append("end_date")
    else:
        end_date = tenancy.end_date

    # short circuit if there are no changes to be made
    if not update_fields:
        return tenancy

    validate_lease_period(apartment.pk, tenancy.start_date, end_date, exclude_tenancy_id=tenancy.pk)
    tenancy.full_clean()
    tenancy.save(update_fields=update_fields)
    logger.info("tenancy_updated", tenancy_id=tenancy.pk, apartment=str(apartment), fields=update_fields)
    return tenancy


@transaction.atomic
def tenancy_extend_reservation(tenancy: Tenancy, reservation_extension: timedelta) -> Tenancy:
    """
    Means for admins to increase select tenants reservation time as they wait for tenant to clear payment.

    :param: tenancy: Tenancy being updated.
    :param: reservation_extension: The range of time to extend the expiration.
    :return: Updated tenancy record.
    """
    if not tenancy.reservation_expiration:
        tenancy.reservation_expiration = timezone.now().date()
    computed_reservation_expiration = tenancy.reservation_expiration + reservation_extension

    tenancy.reservation_expiration = computed_reservation_expiration
    tenancy.full_clean()
    tenancy.save(update_fields=["reservation_expiration"])
    logger.info("tenancy_reservation_extended", duration_days=reservation_extension.days)
    return tenancy


@transaction.atomic
def tenancy_terminate(tenancy: Tenancy, termination_date: date | None = None) -> None:
    """
    Delete tenant record and credit all the payments
    First we need to change it to expired
    """
    from django.db.models import Sum, Q

    tenancy.status = Tenancy.TenancyStatus.TERMINATED
    tenancy.end_date = termination_date or timezone.now().date()
    tenancy.save(update_fields=["status", "end_date"])

    logger.info(
        "tenancy_terminated",
        tenancy_id=tenancy.pk,
        terminated_at=str(termination_date)
    )


def normalize_lease_period(start_date: date, duration_months: int) -> tuple[date, date]:
    """
    Normalize the lease period by setting the start date to the first day of the month and the end date to the last day of the month.
    I had to standardize the duration of the month to 28 to avoid weird lapses
    :param start_date: Lease start date
    :param end_date: Lease end date
    :return: Normalized start and end dates
    :rtype: tuple[date, date]
    """
    from calendar import monthrange

    normalized_start = start_date.replace(day=1)
    end_date = start_date + timedelta(days=duration_months * 28)
    end_month_last_day = monthrange(end_date.year, end_date.month)[1]
    normalized_end = end_date.replace(day=end_month_last_day)
    return normalized_start, normalized_end
