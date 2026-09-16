from typing import TYPE_CHECKING
from decimal import Decimal
from structlog import get_logger
from django.db import transaction
from rest_framework.exceptions import ValidationError
from leasify.common.period import DateRange
from leasify.billing.models import BillingPeriod, MAX_BILLING_PERIOD
from leasify.payments.choices import PaymentStatus
from leasify.tenancy.choices import TenancyStatus
from leasify.billing.choices import BillingStatus

if TYPE_CHECKING:
    from leasify.payments.models import Payment
    from leasify.tenancy.models import Tenancy

logger = get_logger("billing.services")


def billing_period_create(*, tenancy: "Tenancy", date_r: DateRange) -> BillingPeriod:
    """
    Create a billing period for a tenancy.

    Creates and saves a BillingPeriod for the provided tenancy over the given date range.
    The total due is calculated from the apartment rent and the requested duration,
    and the maximum billing duration is enforced before creation.

    :param tenancy: The tenancy for which the billing period is being created.
    :param date_r: The requested date range for the billing period.
    :returns: The created BillingPeriod instance.
    :raises ValidationError: If the requested billing duration exceeds the maximum allowed.
    """
    # Cap max billing period
    if date_r.duration_months > MAX_BILLING_PERIOD:
        raise ValidationError("Max billing period exceeded")

    # compute total rent due
    total_due = (tenancy.apartment.rent * date_r.duration_months).quantize(Decimal("0.01"))

    bp = BillingPeriod(
        tenancy_id=tenancy.pk,
        start_date=date_r.start_date,
        end_date=date_r.end_date,
        total_due=total_due,
    )
    bp.save()
    logger.info(
        "billing_period_created",
        tenancy_id=tenancy.pk,
        duration=bp.duration_months,
        billing_id=bp.pk,
        billing_period=str(bp),
    )
    return bp


@transaction.atomic
def billing_period_cancel(billing: BillingPeriod) -> BillingPeriod:
    """
    Cancel an unpaid billing period.

    Marks the specified billing period as cancelled when it is still in the UNPAID state.
    This action is only valid for billing periods that have not yet been paid.

    :param billing: The billing period to cancel.
    :returns: The updated BillingPeriod instance.
    :raises ValidationError: If the billing period is not currently unpaid.
    """
    if billing.status != BillingStatus.UNPAID:
        raise ValidationError("Billing cannot be canceled")

    billing.status = BillingStatus.CANCELLED
    billing.save(update_fields=["status"])
    logger.info(
        "billing_period_canceled",
        tenancy_id=billing.tenancy_id,
        billing_id=billing.pk,
        billing_period=str(billing),
    )
    return billing


@transaction.atomic
def billing_period_complete(billing: BillingPeriod) -> BillingPeriod:
    """
    Complete a billing period after successful payment.

    Validates that a successful payment exists before marking a billing period as paid.
    If the billing period is the current one, the associated tenancy is also activated.

    :param billing: The billing period to complete.
    :returns: The updated BillingPeriod instance.
    :raises ValidationError: If no successful payment is associated with the billing period.
    """

    payment = billing.payments.filter(status=PaymentStatus.SUCCESS).first()
    if not payment or payment.status != PaymentStatus.SUCCESS:
        raise ValidationError("Successful payment required to complete request")

    billing.status = BillingStatus.PAID
    billing.save(update_fields=["status"])
    logger.info(
        "billing_period_paid",
        tenancy_id=billing.tenancy_id,
        payment_id=payment.pk,
        billing_id=billing.pk,
        billing_period=str(billing),
    )
    if billing.is_current:
        t_logger = get_logger("tenancy.services")
        billing.tenancy.status = TenancyStatus.ACTIVE
        billing.tenancy.save(update_fields=["status"])
        t_logger.info("tenancy_activated", tenancy_id=billing.tenancy_id, billing_id=billing.pk)
    return billing
