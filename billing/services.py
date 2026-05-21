from typing import TYPE_CHECKING
from decimal import Decimal
from structlog import get_logger
from django.db import transaction
from rest_framework.exceptions import ValidationError
from common.period import DateRange
from billing.models import BillingPeriod, MAX_BILLING_PERIOD
from billing.selectors import billing_last_paid_for
from billing.choices import BillingStatus

if TYPE_CHECKING:
    from payments.models import Payment
    from tenancy.models import Tenancy

logger = get_logger("billing.services")

@transaction.atomic
def billing_period_initialize(*, tenancy: "Tenancy", date_r: DateRange) -> BillingPeriod:
    """
    Can't create a billing period if the previous one is not cleared.
    Duration months cannot exceed 4, this prevents locking rent if rent hikes will be introduced mid period.
    """
    # Cap max billing period
    if date_r.duration_months > MAX_BILLING_PERIOD:
        raise ValidationError("Max Billng period exceeded")
    
    total_due = (tenancy.apartment.rent * date_r.duration_months).quantize(Decimal("0.01"))

    bp = BillingPeriod(
        tenancy=tenancy,
        start_date=date_r.start_date,
        end_date=date_r.end_date,
        rent_snapshot=total_due,
    )
    bp.full_clean()
    bp.save()
    logger.info(
        "billing_period_created",
        tenancy_id=tenancy.pk,
        start_date=date_r.start_date,
        end_date=date_r.end_date,

    )
    return bp

@transaction.atomic
def billing_period_increment(*, tenancy: "Tenancy", duration_months: int) -> BillingPeriod:
    """
    This is especially for ensuring sequetial billing preiods for ongoing tenants.
    This will only ever be concerned with the last paid billing period.
    This ensures the tenancy stay is sequential.
    """
    if duration_months > MAX_BILLING_PERIOD:
        raise ValidationError("Max Billing period exceeded")

    # I need to lock at this point to avoid another billing period to be created at the same time.
    # There are no db constraints of domain logic
    last_billing = billing_last_paid_for(tenancy.pk, lock=True)
    
    if not last_billing:
        raise ValidationError("Cannot find a paid billing period")
    
  
    
    r = DateRange.compute_lease_window(last_billing.next_start, duration_months)
    total_due = (tenancy.apartment.rent * r.duration_months).quantize(Decimal("0.01"))
    bp = BillingPeriod(
        tenant=tenancy,
        start_date=r.start_date,
        end_date=r.end_date,
        rent_snapshot=total_due,
    )
    bp.full_clean()
    bp.save()
    logger.info(
        "billing_period_renewed",
        tenancy_id=tenancy.pk,
        start_date=r.start_date,
        end_date=r.end_date,

    )
    return bp

@transaction.atomic
def billing_period_update(billing: BillingPeriod, status: BillingStatus, payment: "Payment | None") -> BillingPeriod:
    

    locked = BillingPeriod.objects.select_for_update().get(pk=billing.pk)

    if locked.status == BillingStatus.PAID:
        raise ValidationError("Cannot complete request. Billing period cannot be changed once created")
    
    if status == BillingStatus.UNPAID:
        raise ValidationError("Operation cannot be completed")
    
    if status == BillingStatus.CANCELED:
        locked.status = status
        locked.save(update_fields=["status"])
        return locked
    
    if not payment or payment.status != "confirmed":
        raise ValidationError("Required confirmed payment instance to complete request")
    
    if payment.amount < billing.total_due:
        raise ValidationError("Amount not enough")

    locked.status = status
    locked.save(update_fields=["status"])
    return locked