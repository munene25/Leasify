from datetime import timedelta, date
from rest_framework.exceptions import ValidationError
from common.exceptions import  MaxReservationsExceededError
from tenancy.models import Tenancy, MAX_RESERVATIONS_PER_USER
from common.period import DateRange, today

    
def validate_max_monthly_reservations(user_id: int, exceed: int = MAX_RESERVATIONS_PER_USER) -> None:
    """
    We need to protect the system from abuse of tenants spamming bookings.

    :param user_id: user to check against
    :raises ValidationError: If the maximum number of reservations has been exceeded.
    """    
    r = DateRange.for_month()
    recent_reservations = Tenancy.objects.filter(
        user_id=user_id,
        created_at__gte = r.start_date,
        created_at__lte = r.end_date,
        status__in=(Tenancy.Status.PENDING , Tenancy.Status.TERMINATED),
    ).count()
    if recent_reservations > exceed:
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
    


def validate_reservation_extension(tenancy: Tenancy, reservation_extension: timedelta) -> None:
    computed_reservation_expiration = tenancy.reservation_expriry + reservation_extension
    if tenancy.status != Tenancy.Status.PENDING:
        raise ValidationError("Only pending tenancies can have their reservations extended.")
    if reservation_extension > timedelta(days=21):
        raise ValidationError("Reservation extension cannot be longer than 3 weeks.")
    # if computed_reservation_expiration >= tenancy.end_date:
    #     raise ValidationError("Reservation extension cannot extend beyond the lease end date.")