from billing.models import BillingPeriod
from common.helpers import raise_not_found
from billing.choices import BillingStatus

billing_not_found = raise_not_found("billing_id", "Billing Period not found")


@billing_not_found
def billing_lock(billing_id: int) -> BillingPeriod:
    return BillingPeriod.objects.select_for_update().get(pk=billing_id)


@billing_not_found
def billing_get(billing_id: int) -> BillingPeriod:
    return BillingPeriod.objects.get(pk=billing_id)


def billing_last_paid_for(tenancy_id: int, lock: bool = True) -> BillingPeriod | None:
    billing = BillingPeriod.objects.filter(tenancy_id=tenancy_id, status=BillingStatus.PAID).order_by("-start_date")
    if lock:
        return billing.select_for_update().first()
    return billing.first()
