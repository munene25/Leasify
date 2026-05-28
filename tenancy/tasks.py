from structlog import get_logger
from celery import shared_task
from django.db import transaction
from django.db.models import QuerySet
from common.period import today
from tenancy.choices import TenancyStatus as TS, TerminationReason as TR
from tenancy.models import Tenancy
from billing.choices import BillingStatus as BS
from billing.models import BillingPeriod as Billings

logger = get_logger("celery.tenancy")
auto_retry = shared_task(retry_kwargs={'max_retries': 5}, retry_backoff=True)

@auto_retry
def month_start_tasks():
    """
    Run at start of month:
    * ** They remain seperate for ease of testing. **
    1. Terminate defaulting tenancies (non-payment)
    2. Set active tenancies without paid billing to defaulting
    """
    
    logger.info("month_start_task")
    try: 
        defaulting_terminated = defaulting_set_terminated()
        active_terminated = active_set_defaulting()

    except Exception as e:
        logger.error("month_start_task_failed", errors=str(e))
        raise Exception from e
    
    logger.info("month_start_task_complete", active=active_terminated, defaulting=defaulting_terminated)


@auto_retry
def reserved_set_terminated() -> list[int | None]:
    """Terminate tenants who are in status RESERVED and set reason to EXPIRED"""

    logger.info("terminating_reserved")
    try:
        qs = Tenancy.objects.filter(status=TS.RESERVED, reservation_expiry__lt=today())
        tenancies = tenancy_terminate_from(tenants=qs, reason=TR.EXPIRED)
    except Exception as e:
        logger.error("terminating_reserved_failed", errors=str(e))
        raise Exception from e
    logger.info("terminatin_reserved_successful", terminated=tenancies)
    return tenancies


@transaction.atomic
def tenancy_terminate_from(tenants: QuerySet[Tenancy], reason: TR) -> list[int | None]:
    """
    Terminate tenancies from queryset
    :param tenants: A queryset of tenants of which to terminate.
    :param reason: The termination reason to for termination.
    :param return: The list of affected tenancies.
    """
    if not (t_list := list(tenants.values_list("pk", flat=True))):
        return []

    tenants.update(status=TS.TERMINATED, termination_date=today(), termination_reason=reason)

    # Cancel to prevent attempts to pay for the terminated bookings.
    unpaid_bills = Billings.objects.filter(tenancy_id__in=t_list, status=BS.UNPAID)
    unpaid_bills.update(status=BS.CANCELED)
    return t_list

def active_set_defaulting() -> list[int | None]:
    """Set tenancies with nopayments for the billing cycle to DEFAULTING"""
    
    # Get defaulting
    qs = Tenancy.objects.filter(status=TS.ACTIVE)

    # Exclude those with paid bills
    qs = qs.exclude(
        billings__start_date__lte=today(),
        billings__end_date__gte=today(),
        billings__status=BS.PAID
    )
    
    if not (t_list := list(qs.values_list("pk", flat=True))):
        return []

    qs.update(status=TS.DEFAULTING)
    return t_list


def defaulting_set_terminated() -> list[int | None]:
    """Terminate tenants who are in status DEFAULTING and set reason to NONPAYMENT"""
    
    qs = Tenancy.objects.filter(status=TS.DEFAULTING)
    return tenancy_terminate_from(tenants=qs, reason=TR.NONPAYMENT)


