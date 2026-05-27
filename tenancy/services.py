from typing import TYPE_CHECKING
from structlog import get_logger
from django.db import transaction
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

@transaction.atomic
def tenancy_lease_extend(tenancy: Tenancy, duration_months: int) -> Tenancy:
    """
    A tenant wants to create a new billing period.
    The start date of the next billing period is computed from the last paid.

    :param tenancy: Tenancy object to extend lease for.
    :param duration_months: Max allowed duration is 4 months validated by billing period.
    :rerturn: Updated tenancy object
    """

    # Background tasks may cause race condition.
    tenancy = Tenancy.objects.select_related("apartment").select_for_update().get(pk=tenancy.pk)

    # This prevents Terminated or Expired tenancies from extending lease
    if not tenancy.is_continuing:
        raise ValidationError("Only continuing tenants can extend their lease")
    
    # This prevents ghost payments.
    if tenancy.has_pending_bills:
        raise ValidationError("You have an UNPAID billing period, cancel it to create a new one")
    
    # No need to lock, its immutable.
    last = tenancy.last_paid_billing
    
    r = DateRange.compute_lease_window(start_date=last.next_start, duration_months=duration_months)

    billing_period_create(tenancy=tenancy, date_r=r)
    return tenancy 

@transaction.atomic
def tenancy_terminate(*, tenancy: Tenancy, termination_reason: TerminationReason, termination_date: "date | None" = None) -> Tenancy:
    """
    Allow tenants to cancel their leases.
    Cleanup involves terminating their billing periods as well.
    Opted for this over objects.update since the return is basically 
    ? Should add a check to ensure termination date cannot preceed creation.

    :param tenancy: Tenant object being terminated.
    :param termination_reason: The reason they are being terminated, determined upstrem (views).
    :param termination_date: To allow for slightly backdating tenancies.
    :return: The Terminated tenancy instance
    """
    
    from common.period import today

    if termination_date and tenancy.created_at.date() > termination_date:
        raise ValidationError(f"Cannot set termination date before tenant's creation date: {tenancy.created_at.date().strftime("%B %d, %Y")}")

    tenancy.status = TenancyStatus.TERMINATED
    tenancy.termination_date = termination_date or today()
    tenancy.termination_reason = termination_reason 
    tenancy.save(update_fields=("status", "termination_date", "termination_reason"))
    tenancy.billings.filter(status=BillingStatus.UNPAID).update(status=BillingStatus.CANCELED)
    return tenancy


