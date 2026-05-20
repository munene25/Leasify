from typing import TYPE_CHECKING
from structlog import get_logger
from django.db import transaction
from rest_framework.exceptions import ValidationError
from common.period import DateRange
from billing.models import BillingPeriod, MAX_BILLING_PERIOD

if TYPE_CHECKING:
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
    
    bp = BillingPeriod(
        tenancy=tenancy,
        start_date=date_r.start_date,
        end_date=date_r.end_date,
        rent_snapshot=tenancy.apartment.rent,
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
    This is especially for ensuring sequetial billing preiods for ongoing tenants
    """
    if duration_months > MAX_BILLING_PERIOD:
        raise ValidationError("Max Billing period exceeded")

    last = (
        BillingPeriod.objects
        .filter(tenant=tenancy)
        .select_for_update()
        .order_by("-start_date")
        .first()
    )
    if not last:
        raise ValidationError("New Tenants are required to initialize their billing periods first")

    # Check if last billing cleared.
    if not last.is_cleared:
        raise ValidationError("Previous billing period is not cleared.")
    
    r = DateRange.compute_lease_window(last.next_start, duration_months)
    
    bp = BillingPeriod(
        tenant=tenancy,
        start_date=r.start_date,
        end_date=r.end_date,
        rent_snapshot=tenancy.apartment.rent,
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
