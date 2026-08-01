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
    Can't create a billing period if the previous one is not cleared.
    Duration months cannot exceed 4, this prevents locking rent if rent hikes will be introduced mid period.
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
    Cancel an existing unpaid billing period.
    Irrelevant to lock billing period, can only move one of two ways: paid or canceled.
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
    """Update billing period status to PAID and update tenancy status if billing current"""

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
