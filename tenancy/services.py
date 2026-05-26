from typing import TYPE_CHECKING
from structlog import get_logger
from django.db import transaction
from django.contrib.auth.models import Group
from rest_framework.exceptions import ValidationError
from common.exceptions import ApartmentUnavailableError
from common.period import DateRange
from users.services import user_set_role
from tenancy import validators as v
from tenancy.models import Tenancy
from tenancy.choices import TenancyStatus, TerminationReason
from tenancy.selectors import tenancy_in
from apartments.selectors import apartment_lock
from billing.services import billing_period_create
from billing.choices import BillingStatus

logger = get_logger("tenancy.services")

if TYPE_CHECKING:
    from users.models import User
    from datetime import date
    from apartments.models import Apartment
    from billing.models import BillingPeriod


@transaction.atomic
def tenancy_create(*, user: "User", apartment: "Apartment", start_date: "date", duration_months: int) -> Tenancy:
    """

    Create a tenancy as well as a billing period the selected duration
    Check if dates are valid for creation
    Add user to tenant group.

    :param user: The tenant user
    :param apartment: The apartment to be rented, should be rentable.
    :param start_date: Lease start date
    :param duration_months: Lease duration in months
    :return: The created tenancy record.
    """

    # Users can only make a certain number of reservations in a month.
    v.validate_max_monthly_reservations(user.pk)

    # Even though the lease period is tied to the billing period.
    # I need to check that they are not booking too far in advance
    v.validate_lease_period(start_date)
    
    # We need to lock the apartment to 
    apt = apartment_lock(apartment.pk)

    if not apt.rentable:
        raise ApartmentUnavailableError()
    
    v.validate_db_constraint(user_id=user.pk, apartment_id=apt.pk)
    
    t = Tenancy(
        user=user,
        apartment=apt,
        status=TenancyStatus.RESERVED,
    )
    # Its important to note that we are no longer validating via full clean.
    # Db constraints still exist but validation happens via validate_db_constraints.
    # * This is in an effort to reduce number of queries.
    t.save()

    # Add user to Tenant group if not already
    # Replace set to true coz i already know there is no existing tenancy 
    if not user.groups.filter(name="tenant").exists():
        from users.selectors import get_group
        user_set_role(user=user, role=get_group(name="tenant"), replace=True)

    logger.info(
        "tenancy_created",
        tenancy_id=t.pk,
        tenant_name=user.full_name,
        status=t.status,
    )

    r = DateRange.compute_lease_window(start_date, duration_months)
    billing_period_create(tenancy=t, date_r=r)
    return t

def tenancy_lease_extend(tenancy: Tenancy, duration_months: int) -> "BillingPeriod":
    """
    A tenant wishes to extend their stay.
    The start date of the next billing period is computed from the last paid.
    To ensure no pending periods remain, check if there are unpaid billing periods first.
    This avoids paying for ghost billing periods.
    """

    from billing.selectors import billing_last_paid_for

    tenancy = Tenancy.objects.select_for_update().get(pk=tenancy.pk)

    # Tenant should have an existing billing history and in status defaulting or active
    if not tenancy.is_continuing:
        raise ValidationError("Only continuing tenancies can extend their stay")
    
    if tenancy.has_pending_bills:
        raise ValidationError("You have an pending billing period, cancel it to create a new one")

    
    last_billing = billing_last_paid_for(tenancy.pk, lock=True)
 
    if not last_billing:
        raise ValidationError("Cannot find a paid billing period")
    
    r = DateRange.compute_lease_window(start_date=last_billing.next_start, duration_months=duration_months)

    return billing_period_create(tenancy=tenancy, date_r=r)

@transaction.atomic
def tenancy_terminate(tenancy: Tenancy):
    """A service to allow tenants to cancel their leases"""

    tenancy.status = TenancyStatus.TERMINATED
    if tenancy.has_pending_bills:
        tenancy.objects.filter(status=BillingStatus.UNPAID).update(status=BillingStatus.CANCELED)
    tenancy.save(update_fields=["status"])

@transaction.atomic
def tenancy_reserved_to_terminated() -> None:
    """
    Fetch all tenancies that are reserved, then filter the ones whose expiration date is past due.
    Terminate then update termination date and reason.
    """
    from common.period import today

    now = today()

    t = tenancy_in([TenancyStatus.RESERVED]).filter(
        reservation_expiry__gt=now,
    )

    t.update(
        status=TenancyStatus.TERMINATED,
        termination_date=now,
        termination_reason=TerminationReason.EXPIRED,
    )
    # cancel billing periods
    # This prevents attempts to pay for the terminated bookings
    BillingPeriod.objects.filter(
        tenancy_id__in=t.values_list("pk", flat=True),
        status=BillingStatus.UNPAID
    ).update(status=BillingStatus.CANCELED)


def tenancy_active_to_defaulting() -> None:
    """
    Fetch all tenancies that are active.
    Filter the ones that have no paid billing period and terminate them.
    They are not being terminated, just status change
    ? Date as param, then task does this?
    """
    from common.period import today

    now = today()

    tenancy_in([TenancyStatus.ACTIVE]).exclude(
        billingperiod__start_date__lte=now,
        billingperiod__end_date__lte=now,
        billingperiod__status=BillingStatus.PAID,
    ).update(status=TenancyStatus.DEFAULTING)
