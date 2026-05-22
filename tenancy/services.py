from typing import TYPE_CHECKING
from structlog import get_logger
from django.db import transaction
from django.contrib.auth.models import Group
from rest_framework.exceptions import ValidationError
from common.period import DateRange
from users.services import user_set_role
from tenancy.validators import validate_max_monthly_reservations, validate_lease_period
from tenancy.models import Tenancy
from tenancy.choices import TenancyStatus, TerminationReason
from tenancy.selectors import tenancy_in
from apartments.selectors import apartment_lock
from billing.services import billing_period_increment, billing_period_initialize
from billing.choices import BillingStatus

logger = get_logger("tenancy.services")

if TYPE_CHECKING:
    from users.models import User
    from datetime import date
    from apartments.models import Apartment
    from billing.models import BillingPeriod


@transaction.atomic()
def tenancy_create(*, user: "User", apartment: "Apartment", start_date: "date", duration_months: int) -> Tenancy:
    """

    Create a tenancy as well as a billing period the selected duration
    Check if dates are valid for creation
    Add user to tenant group.

    :param user: The tenant user
    :param apartment: The apartment to be rented
    :param start_date: Lease start date
    :param duration_months: Lease duration in months
    :param status: The initial status of the tenancy
    :param total_due: The total amount due for the tenancy. If not provided, it will be calculated based on the apartment rent and lease duration.
    :return: The created tenancy record.
    """

    # Users can only make a certain number of reservations in a month.
    validate_max_monthly_reservations(user.pk)

    # Even though the lease period is tied to the billing period.
    # I need to check that they are not booking too far in advance
    validate_lease_period(start_date)

    apt = apartment_lock(apartment.pk)
    t = Tenancy(
        user=user,
        apartment=apt,
        status=TenancyStatus.RESERVED,
    )
    t.full_clean()
    t.save()

    # Add user to Tenant group if not already
    if not user.groups.filter(name="tenant").exists():
        user_set_role(user=user, role=Group.objects.get(name="tenant"))

    logger.info(
        "tenancy_created",
        tenancy_id=t.pk,
        tenant_name=user.full_name,
        status=t.status,
    )

    r = DateRange.compute_lease_window(start_date, duration_months)
    billing_period_initialize(tenancy=t, date_r=r)
    return t


def tenancy_renew_lease(tenancy: Tenancy, duration_months: int) -> "BillingPeriod":
    """A tenant wishes to create a new billing period for themselves"""
    from billing.choices import BillingStatus

    # Tenant should have an existing billing history and either
    if not tenancy.is_continuing or not tenancy.last_billing:
        raise ValidationError("Only continuing tenancies can create a tenancy")

    if tenancy.last_billing.status == BillingStatus.UNPAID:
        raise ValidationError("You have an pending billing period, cancel it to create a new one")

    tenancy = Tenancy.objects.select_for_update().get(pk=tenancy.pk)

    return billing_period_increment(tenancy=tenancy, duration_months=duration_months)


def tenancy_reserved_to_terminated() -> None:
    """
    Fetch all tenancies that are reserved, then filter the ones whose expiration date is past due.
    Terminate then update termination date and reason.
    """
    from common.period import today

    now = today()

    t = tenancy_in([TenancyStatus.RESERVED]).filter(
        reservation_expiration__gt=now,
    )

    t.update(
        status=TenancyStatus.TERMINATED,
        termination_date=now,
        termination_reason=TerminationReason.EXPIRED,
    )


def tenancy_active_to_defaulting() -> None:
    """
    Fetch all tenancies that are active.
    Filter the ones that have no paid billing period and terminate them.
    Update termination date and reason
    ? Date as param, then task does this?
    """
    from common.period import today

    now = today()

    t = tenancy_in([TenancyStatus.ACTIVE]).exclude(
        billingperiod__start_date__lte=now,
        billingperiod__end_date__lte=now,
        billingperiod__status=BillingStatus.PAID,
    )

    t.update(status=TenancyStatus.DEFAULTING, termination_date=now, termination_reason=TerminationReason.NONPAYMENT)
