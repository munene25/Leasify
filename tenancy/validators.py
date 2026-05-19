from datetime import timedelta
from rest_framework.exceptions import ValidationError
from common.exceptions import ApartmentOccupiedError, InvalidPeriodError, MaxReservationsExceededError
from tenancy.models import Tenancy, GRACE_PERIOD, MAX_RESERVATIONS_PER_USER
from common.period import DateRange, today

def validate_lease_period(*, apartment_id: int, date_range: DateRange, exclude_tenancy_id: int | None = None) -> None:
    """
    Validate that the lease period is valid (start date before end date and not in the past).
    As well as no overlapping tenancy exists at the time.
    ? might consider the extended end date (end_date + grace_time)
    ? The caller is responsible for determining what date range is passed. Either with grace period or not

    :param apartment_id: The apartment to check for overlapping leases. better to pass it as id rather than apartment.
    :param start_date: Lease start date
    :param end_date: Lease end date
    :raises InvalidPeriod: If the lease period is invalid
    """
    # ! Without this, past tenancies can be created.
    # if date_range.end_date < today():
    #     raise InvalidPeriodError()
    
    
    overlapping = Tenancy.objects.filter(apartment_id=apartment_id, start_date__lt=date_range.end_date, end_date__gt=date_range.start_date)

    if exclude_tenancy_id:
        overlapping = overlapping.exclude(pk=exclude_tenancy_id)

    if overlapping.exists():
        raise ApartmentOccupiedError()
    
def validate_max_number_of_reservations(user_id: int) -> None:
    """
    Verify that the number of reservations for the apartment in the past 2 weeks has not exceeded the maximum allowed.

    :param apartment: The apartment to check
    :raises ValidationError: If the maximum number of reservations has been exceeded.
    """

    from django.db.models import Q

    # Check max number of reservations in the past 2 weeks has not reached for the apartment before creating the tenancy record.
    now = today()
    start = now - GRACE_PERIOD

    recent_reservations = Tenancy.objects.filter(
        user_id=user_id,
        reservation_expiration__gte=start,
        reservation_expiration__lte=now,
        status__in=(Tenancy.Status.PENDING , Tenancy.Status.EXPIRED),
    ).count()
    if recent_reservations > MAX_RESERVATIONS_PER_USER:
        raise MaxReservationsExceededError()

def validate_reservation_extension(tenancy: Tenancy, reservation_extension: timedelta) -> None:
    computed_reservation_expiration = tenancy.reservation_expiration + reservation_extension
    if tenancy.status != Tenancy.Status.PENDING:
        raise ValidationError("Only pending tenancies can have their reservations extended.")
    if reservation_extension > timedelta(days=21):
        raise ValidationError("Reservation extension cannot be longer than 3 weeks.")
    if computed_reservation_expiration >= tenancy.end_date:
        raise ValidationError("Reservation extension cannot extend beyond the lease end date.")