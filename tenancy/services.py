from decimal import Decimal
from typing import TypedDict, Unpack, TYPE_CHECKING
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from tenancy.models import Tenancy
from tenancy.selectors import tenancy_lock
from semesters import selectors as sem_selectors
from apartments.selectors import apartment_for_update
from users.services import user_set_role
from payments.services import PaymentCreateService
from users.services import user_set_role
from common.exceptions import SemesterEndedError, ApartmentOccupiedError


if TYPE_CHECKING:
    from users.models import User
    from semesters.models import Semester
    from apartments.models import Apartment

class TenancyUpdate(TypedDict, total=False):
    semester: Semester
    apartment: Apartment

def validate_apartment_and_semester(apartment: "Apartment", semester: "Semester") -> None:
    """
    Only future and current semesters should be available for booking

    The apartment rentable flag is a global lock allowing or disallowing tenants to book.
    Non rentable apartments are already filtered out of tenants and guest querysets.
    Nontheless we should explicitly check first if the apartment is availalbe for rent.
    And fallback to occupancy in cases where a manager is assigning an apartment.
    This is still enforced at the database level with unique constraints.
    """
        
    if semester.has_ended:
        raise SemesterEndedError()
    if not apartment.rentable:
        raise ValidationError({"apartment_id": "Apartment not available for renting"})
    if apartment.tenancy_set.filter(semester_id=semester.pk).exists():
        raise ApartmentOccupiedError()
    

@transaction.atomic
def create(*, user: "User", apartment: "Apartment", semester: "Semester", total_paid: Decimal = Decimal(0)) -> Tenancy:
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

    # First validate apartment and semester availablity
    validate_apartment_and_semester(apartment, semester)

    # Create tenancy
    tenancy = Tenancy(
        user=user,
        apartment=apartment,
        semester=semester,
        total_paid=total_paid,
    )
    tenancy.full_clean()
    tenancy.save()

    # Add user to Tenant group
    
    if not user.groups.filter(name="tenant").exists():
        user_set_role(user=user, role=Group.objects.get(name="tenant"))
    return tenancy

@transaction.atomic
def tenancy_update(tenancy: Tenancy, **kwargs: Unpack[TenancyUpdate] ) -> Tenancy:
    """
    Update tenant's semester or apartment
    
    :param tenancy: Tenant object being updated
    :type tenancy: Tenancy

    :param kwargs: semester: Semester, apartment: Apartment
    :type kwargs: Any
    
    :return: Description
    :rtype: Tenancy
    """

    editable_fields = {"semester", "apartment"}
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
    tenancy.save(update_fields=list(update_fields.keys()))
    return tenancy

@transaction.atomic
def delete(tenancy: Tenancy) -> None:
    """Delete tenant record and credit the payments"""

    if tenancy.total_paid > Decimal(0):
        PaymentCreateService(
            amount=tenancy.total_paid,
            transaction_type="credit",
            tenancy_id=tenancy.pk,
            initiator="system",
        ).create()
    tenancy.delete()




    

    
    

