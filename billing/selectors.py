from billing.models import BillingPeriod

from common.helpers import raise_not_found 

billing_not_found = raise_not_found("billing_id", "Billing Period not found")

def billing_last_for(tenancy_id: int) -> BillingPeriod | None:
    return BillingPeriod.objects.filter(tenant=tenancy_id).order_by("-start_date").first()


@billing_not_found
def billng_lock(billing: BillingPeriod) -> BillingPeriod:
    return BillingPeriod.objects.select_for_update().get(pk=billing.pk)
    
