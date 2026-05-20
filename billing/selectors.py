from billing.models import BillingPeriod
from tenancy.models import Tenancy

def billing_last_for(tenancy_id: int) -> BillingPeriod | None:
    last = BillingPeriod.objects.select_for_update().filter(tenant=tenancy_id).order_by("-start_date").first()
    return last
    
