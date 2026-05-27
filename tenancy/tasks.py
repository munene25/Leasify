from django.db import transaction
from common.period import today
from tenancy.choices import *
from tenancy.selectors import tenancy_in
from billing.choices import BillingStatus
from billing.models import BillingPeriod
from celery import shared_task
from celery.utils.log import get_task_logger
from structlog import get_logger
from django.db.models import Q

logger = get_logger("tenancy.tasks")
task_logger = get_task_logger(__name__)

def tenancy_active_set_defaulting() -> list[int | None]:
    """
    Fetch all active tenancies that dont have a paid billing period currently.
    Set tenancies to defaulting.
    """
    from common.period import today

    now = today()

    t = tenancy_in([TenancyStatus.ACTIVE]).exclude(
        billings__start_date__lte=now,
        billings__end_date__gte=now,
        billings__status=BillingStatus.PAID,
    )
    
    tenancies = list(t.values_list("pk", flat=True))

    t.update(status=TenancyStatus.DEFAULTING)
    if tenancies:
        logger.info(
            "tenancy_active_set_defauling",
            tenancies=tenancies
        )
    return tenancies



@transaction.atomic
def tenancy_set_terminated_from(*, initial: TenancyStatus, reason: TerminationReason, filters: Q | None = None) -> list[int | None]:
    """
    This is intended to run as a scheduled task.
    Fetch all tenancies that are in initial status and terminate them.
    Terminate then update termination date and reason.
    """
    from common.period import today
    
    # ! Fetching value_list after update will always return empty list
    t = tenancy_in([initial]).filter(filters or Q())
    tenancies = list(t.values_list("pk", flat=True))

    t.update(
        status=TenancyStatus.TERMINATED,
        termination_date=today(),
        termination_reason=reason,
    )
    
    # Cancel to prevent attempts to pay for the terminated bookings.
    BillingPeriod.objects.filter(
        tenancy_id__in=tenancies,
        status=BillingStatus.UNPAID
    ).update(status=BillingStatus.CANCELED)

    if tenancies:
        logger.info(
            "tenancies_terminated",
            tenancies=tenancies,
            reason=reason,
        )
    return tenancies

# @shared_task
# def terminate_defaulting() -> None:
#     return tenancy_defaulting_to_terminated()

# @shared_task
# def default_active() -> None:
#     return tenancy_active_to_defaulting()

# @shared_task
# def terminate_reserved() -> None:
#     return tenancy_reserved_to_terminated()