from typing import TYPE_CHECKING
from structlog import get_logger
from datetime import date
from django.db import transaction
from tenancy.models import Tenancy, GRACE_PERIOD
from tenancy.validators import validate_max_monthly_reservations, validate_lease_period
from django.contrib.auth.models import Group
from users.services import user_set_role
from apartments.selectors import apartment_lock
from billing.services import billing_period_initialize
from common.period import DateRange

logger = get_logger("tenancy.services")

if TYPE_CHECKING:
    from users.models import User
    from apartments.models import Apartment


@transaction.atomic()
def tenancy_create(*, user: "User", apartment: "Apartment", start_date: date, duration_months: int) -> Tenancy:
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
    validate_max_monthly_reservations(user.pk)
    validate_lease_period(start_date)


    apt = apartment_lock(apartment.pk)
    t = Tenancy(
        user=user,
        apartment=apt,
        status=Tenancy.Status.PENDING,
    )
    t.full_clean()
    t.save()

    #Add user to Tenant group if not already
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