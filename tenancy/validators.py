from datetime import date, timedelta
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from common.exceptions import ApartmentOccupiedError, InvalidPeriodError, MaxReservationsExceededError
from tenancy.models import Tenancy, GRACE_PERIOD, MAX_RESERVATIONS_PER_USER

def validate_lease_period(
    apartment_id: int, start_date: date, end_date: date, exclude_tenancy_id: int | None = None
) -> None:
    """
    Validate that the lease period is valid (start date before end date and not in the past).
    As well as no overlapping tenancy exists at the time.
    ? might consider the extended end date (end_date + grace_time)

    :param apartment_id: The apartment to check for overlapping leases. better to pass it as id rather than apartment.
    :param start_date: Lease start date
    :param end_date: Lease end date
    :raises InvalidPeriod: If the lease period is invalid
    """
    if end_date <= start_date or end_date < timezone.now().date():
        raise InvalidPeriodError()

    overlapping = Tenancy.objects.filter(apartment_id=apartment_id, start_date__lt=end_date, end_date__gt=start_date)

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
    now = timezone.now().date()
    start = now - GRACE_PERIOD

    recent_reservations = Tenancy.objects.filter(
        user_id=user_id,
        reservation_expiration__gte=start,
        reservation_expiration__lte=now,
        status=Q(Tenancy.TenancyStatus.PENDING) | Q(Tenancy.TenancyStatus.EXPIRED),
    ).count()
    if recent_reservations > MAX_RESERVATIONS_PER_USER:
        raise MaxReservationsExceededError()

def validate_reservation_extension(tenancy: Tenancy, reservation_extension: timedelta) -> None:
    computed_reservation_expiration = tenancy.reservation_expiration + reservation_extension
    if tenancy.status != Tenancy.TenancyStatus.PENDING:
        raise ValidationError("Only pending tenancies can have their reservations extended.")
    if reservation_extension > timedelta(days=21):
        raise ValidationError("Reservation extension cannot be longer than 3 weeks.")
    if computed_reservation_expiration >= tenancy.end_date:
        raise ValidationError("Reservation extension cannot extend beyond the lease end date.")