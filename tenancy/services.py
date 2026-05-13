from decimal import Decimal
from typing import TypedDict, Unpack, TYPE_CHECKING
from structlog import get_logger
from django.db import transaction
from tenancy.models import Tenancy
from tenancy.selectors import tenancy_lock
from payments.services import PaymentCreateService
from common.exceptions import SemesterEndedError, ApartmentOccupiedError

logger = get_logger("tenancy.services")

if TYPE_CHECKING:
    from users.models import User
    from semesters.models import Semester
    from apartments.models import Apartment
    from payments.models import Payment

class TenancyUpdate(TypedDict, total=False):
    semester: "Semester"
    apartment: "Apartment"
    lease_rent: Decimal

def validate_apartment_and_semester(apartment: "Apartment", semester: "Semester") -> None:
    """
    Only future and current semesters should be available for booking.

    The apartment rentable flag is a global lock allowing or disallowing tenants to book.
    But in this case the selector will figure out which apartment is availbable for the user anyways.
    """
        
    if semester.has_ended:
        raise SemesterEndedError()
    if apartment.tenancy_set.filter(semester_id=semester.pk).exists():
        raise ApartmentOccupiedError()
    

@transaction.atomic
def tenancy_create(*, user: "User", apartment: "Apartment", semester: "Semester", total_paid: Decimal = Decimal(0), lease_rent: Decimal | None = None) -> Tenancy:
    """
    Create a tenancy record for a user, apartment, and semester.
    Add user to tenant group.
    
    :param self: TenancyService instance
    :param user: The user occupying the apartment
    :type user: User
    :param apartment: Apartment to be booked. will be flagged not rentable if successful to prevent slotting. 
    :type apartment: Apartment
    :param semester: Semester associated with the tenancy
    :type semester: Semester
    :param total_paid: Total sum of money received from the tenant.
    :type total_paid: Decimal
    :return: Returns the created tenancy record
    :rtype: Tenancy
    """
    from django.contrib.auth.models import Group
    from users.services import user_set_role
    from apartments.services import apartment_update

    # First validate apartment and semester availablity
    validate_apartment_and_semester(apartment, semester)
    # Create tenancy
    tenancy = Tenancy(
        user=user,
        apartment=apartment,
        semester=semester,
        lease_rent=lease_rent or apartment.rent,
        total_paid=total_paid
    )

    tenancy.full_clean()
    tenancy.save()
    # Add user to Tenant group
    if not user.groups.filter(name="tenant").exists():
        user_set_role(user=user, role=Group.objects.get(name="tenant"))

    logger.info("tenancy_created", tenancy_id=tenancy.pk, tenant_name=user.full_name, semester=str(semester), apartment=str(apartment))
    apartment_update(apartment=apartment, rentable=False)
    return tenancy

@transaction.atomic
def tenancy_update(tenancy: Tenancy, **kwargs: Unpack[TenancyUpdate] ) -> Tenancy:
    """
    Updates a tenant's semester or apartment
    
    :param tenancy: Tenant object being updated
    :type tenancy: Tenancy
    :param kwargs: semester: Semester, apartment: Apartment
    :type kwargs: Any
    :return: Description
    :rtype: Tenancy
    """

    editable_fields = {"semester", "apartment", "lease_rent"}
    update_fields = {
        k: v
        for k, v in kwargs.items()
        if k in editable_fields and getattr(tenancy, k) != v
    }
    if not update_fields:
        return tenancy
    
    apartment = update_fields.get("apartment") or tenancy.apartment
    semester = update_fields.get("semester") or tenancy.semester
    validate_apartment_and_semester(apartment, semester) #type: ignore

    # individual updates for semester and apartment
    for field, value in update_fields.items():
        setattr(tenancy, field, value)

    tenancy.full_clean()
    update_fields = list(update_fields.keys())
    tenancy.save(update_fields=update_fields)
    logger.info("tenancy_updated", tenancy_id=tenancy.pk, fields=update_fields)
    return tenancy

@transaction.atomic
def tenancy_update_balance(payment: "Payment") -> Tenancy:
    """
    Updates the total amount paid for the tenant once payment status changes to completed.
    At this point, it does not make sense to raise an error if payment amount exceeds rent since payment is already accepted.
    
    :param payment: The confirmed payment instance
    :type payment: Payment
    :return: the updated tenant object
    :rtype: Tenancy
    """

    tenancy = tenancy_lock(payment.tenancy_id)
    if payment.transaction_type == Payment.TransactionChoices.DEBIT:
        tenancy.total_paid += payment.amount
    else:
        tenancy.total_paid -= payment.amount
    
    tenancy.save(update_fields=["total_paid"])

    logger.info("tenant_balance_updated", tenancy_id=tenancy.pk, payment=payment.ref_no, amount_due=int(tenancy.balance))
    return tenancy


@transaction.atomic
def tenancy_delete(tenancy: Tenancy) -> None:
    """Delete tenant record and credit all the payments"""

    if tenancy.total_paid > Decimal(0):
        PaymentCreateService(
            amount=tenancy.total_paid,
            transaction_type="credit",
            tenancy_id=tenancy.pk,
            initiator="system",
        ).create()
    tenancy.delete()




    

    
    

