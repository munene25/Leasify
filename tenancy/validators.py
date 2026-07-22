from datetime import date
from typing import TYPE_CHECKING
from rest_framework.exceptions import ValidationError
from common.exceptions import MaxReservationsExceededError
from tenancy.models import Tenancy, MAX_RESERVATIONS_PER_USER
from tenancy.choices import TenancyStatus, ACTIVE_RESERVED_OR_DEFAULTING
from tenancy.selectors import tenancy_in
from django.db.models import Count, Q
from common.period import DateRange, today

if TYPE_CHECKING:
    from apartments.models import Apartment


def validate_max_monthly_reservations(user_id: int, exceed: int = MAX_RESERVATIONS_PER_USER) -> None:
    """
    We need to protect the system from abuse of tenants spamming bookings.

    :param user_id: user to check against
    :exceed: number of reservations that would be considered exceeding the limit (default is MAX_RESERVATIONS_PER_USER)
    :raises ValidationError: If the maximum number of reservations has been exceeded.
    """
    r = DateRange.for_month()
    result = Tenancy.objects.filter(
        user_id=user_id,
        created_at__date__gte=r.start_date,
        created_at__date__lte=r.end_date,
    ).aggregate(
        reserved=Count("pk", filter=Q(status=TenancyStatus.RESERVED)),
        terminated=Count("pk", filter=Q(status=TenancyStatus.TERMINATED)),
    )

    if result["reserved"] >= 1 or result["terminated"] >= 2:
        raise MaxReservationsExceededError()


def validate_lease_period(start_date_raw: date) -> None:
    """
    This prevents abuse of new tenants being able to lock an apartment from listings
    by setting dates in the future
    """
    now = today()
    target_month = DateRange.for_month(start_date_raw)
    this_month = DateRange.for_month(now)
    next_month = this_month.next_month()

    # At any point in time, you can only create tenancies for this or next month
    if target_month not in (this_month, next_month):
        raise ValidationError("Cannot create booking for this time")

    # Filter out bookings made before 21st for next month
    if target_month == next_month and now.day < 21:
        raise ValidationError("Bookings for next month open on the 21st.")


def validate_db_constraint(*, user_id: int, apartment_id: int):
    qs = tenancy_in(ACTIVE_RESERVED_OR_DEFAULTING)
    conflict = qs.filter(Q(apartment_id=apartment_id) | Q(user_id=user_id)).exists()
    if conflict:
        raise ValidationError("This Aparment or User is already associated with a tenancy")
