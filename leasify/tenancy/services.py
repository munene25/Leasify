from typing import TYPE_CHECKING
from structlog import get_logger
from django.db import transaction
from rest_framework.exceptions import ValidationError
from leasify.common.exceptions import ApartmentUnavailableError
from leasify.common.period import DateRange
from leasify.users.services import user_set_role
from leasify.tenancy import validators as v
from leasify.tenancy.models import Tenancy
from leasify.tenancy.choices import TenancyStatus as TS, TerminationReason as TR
from leasify.apartments.models import Apartment
from leasify.billing.services import billing_period_create
from leasify.billing.choices import BillingStatus
from leasify.billing.selectors import billing_last_paid

logger = get_logger("tenancy.services")

if TYPE_CHECKING:
    from leasify.users.models import User
    from datetime import date
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
    from leasify.users.selectors import get_group

    # Users can only make a certain number of reservations in a month.
    v.validate_max_monthly_reservations(user.pk)

    # Even though the lease period is tied to the billing period.
    # I need to check that they are not booking too far in advance
    v.validate_lease_period(start_date)

    # We need to lock the apartment to prevent state change
    apt = Apartment.objects.select_for_update().get(pk=apartment.pk)

    if not apt.rentable:
        raise ApartmentUnavailableError()

    v.validate_db_constraint(user_id=user.pk, apartment_id=apt.pk)

    t = Tenancy(
        user=user,
        apartment=apt,
        status=TS.RESERVED,
        date_joined=start_date,
    )
    # Its important to note that we are no longer validating via full clean.
    # Db constraints still exist but validation happens via validate_db_constraints.
    # * This is in an effort to reduce number of queries.
    t.save()

    # Add user to Tenant group if not already
    # Reworked the user role assignment to skip reassignment.
    # * Replace is set to false to prevent overwriting existing roles.
    user_set_role(user=user, role=get_group(name="tenant"))

    logger.info(
        "tenancy_created",
        tenancy_id=t.pk,
        tenant_name=user.full_name,
        date_joined=t.date_joined
    )

    r = DateRange.compute_lease_window(start_date, duration_months)
    billing_period_create(tenancy=t, date_r=r)
    return t


@transaction.atomic
def tenancy_lease_extend(tenancy: Tenancy, duration_months: int) -> tuple[Tenancy, "BillingPeriod"]:
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
        raise ValidationError("You have an unpaid billing period, cancel it to create a new one")

    # No need to lock, its immutable.
    last = billing_last_paid(tenancy.pk)

    r = DateRange.compute_lease_window(start_date=last.next_start, duration_months=duration_months)

    billing = billing_period_create(tenancy=tenancy, date_r=r)
    logger.info("tenancy_lease_extended", tenancy_id=tenancy.pk, duration_months=duration_months)
    return tenancy, billing


@transaction.atomic
def tenancy_terminate(*, tenancy: Tenancy, termination_reason: TR, termination_date: "date | None" = None) -> Tenancy:
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

    from leasify.common.period import today

    if termination_date and termination_date < tenancy.created_at.date():
        created_at = tenancy.created_at.date().strftime("%B %d, %Y")
        raise ValidationError(f"Cannot set termination date before tenant's creation date: {created_at}")

    tenancy.status = TS.TERMINATED
    tenancy.termination_date = termination_date or today()
    tenancy.termination_reason = termination_reason
    tenancy.save(update_fields=("status", "termination_date", "termination_reason"))

    unpaid_billings = tenancy.billings.filter(status=BillingStatus.UNPAID)
    unpaid_billings.update(status=BillingStatus.CANCELLED)
    logger.info(
        "tenancy_terminated",
        tenancy_id=tenancy.pk,
        termination_reason=tenancy.termination_reason,
        termination_date=tenancy.termination_date,
    )
    return tenancy
