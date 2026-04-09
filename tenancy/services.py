from datetime import timezone, date
from typing import Any
from decimal import Decimal
from django.db import transaction
from django.contrib.auth.models import Group
from rest_framework.exceptions import ValidationError
from tenancy.models import Tenancy
from .selectors import tenancy_for_update
from semesters import selectors as sem_selectors
from apartments.selectors import apartment_for_update
from users import selectors as user_selectors
from payments.services import PaymentCreateService
from users.services import user_set_role

class TenancyService:
    def __init__(self, tenancy_id: int | None = None):
        self.EDITABLE_FIELDS = {"semester_id", "apartment_id"}
        self.tenancy_id = tenancy_id
    
    def tenancy_get_locked(self) -> Tenancy:
        if not self.tenancy_id:
            raise ValidationError({"tenancy_id": "Tenancy not provided"})
        return tenancy_for_update(self.tenancy_id)
    
    def _validate_semester_dates(self, semester_id: int) -> None:
        selected_semester = sem_selectors.semester_get_by_id(semester_id)
        now = date.today()
        if now > selected_semester.end_date:
            err = "Invalid semester. Please select a semester that has not yet concluded"
            raise ValidationError({"semester_id": [err]})
        
    def _validate_apartment_vacancy(self, *, apartment, semester_id: int) -> None:
        if apartment.rentable == False and apartment.tenancy_set.filter(
            semester_id=semester_id,
        ).exists():
            raise ValidationError({"apartment_id": ["Aparment is not available in selected semester"]})

    @transaction.atomic
    def create(self, user_id: int, apartment_id: int, semester_id : int) -> Tenancy:
        """
        Create a tenancy record for a user, apartment, and semester.
        
        :param self: TenancyService instance
        :param user_id: The user associated with the tenancy
        :type user_id: int
        :param apartment_id: Apartment associated with the tenancy will be locked during the transaction
        :type apartment_id: int
        :param semester_id: Semester associated with the tenancy
        :type semester_id: int
        :return: Returns the created tenancy record
        :rtype: Tenancy
        """
        # Lock apartment and validate semester
        self._validate_semester_dates(semester_id)
        apt = apartment_for_update(apartment_id)
        self._validate_apartment_vacancy(
            semester_id=semester_id,
            apartment=apt
        )

        # Create tenancy
        tenancy = Tenancy(
            user_id=user_id,
            apartment_id=apartment_id,
            semester_id=semester_id,
            total_paid=Decimal("0.00"),
        )
        tenancy.full_clean()
        tenancy.save()

        # Add user to Tenant group
        user = user_selectors.user_get(user_id)
        tenancy_group, _ = Group.objects.get_or_create(name="tenant")
        if not user.groups.filter(name="tenant").exists():
            user_set_role(user=user, role=tenancy_group)
        return tenancy

    @transaction.atomic
    def update(self, **kwargs: int ) -> Tenancy:
        """
        Update tenant's semester or apartment
        
        :param self: TenancyService instance
        :param kwargs: semester_id: int, apartment_id: int
        :type kwargs: int
        :return: Description
        :rtype: Tenancy
        """
        tenancy = self.tenancy_get_locked()

        update_fields = {
            k: v
            for k, v in kwargs.items()
            if k in self.EDITABLE_FIELDS and getattr(tenancy, k) != v
        }
        if not update_fields:
            return tenancy
        
        # Lock new apartment if one is provided else use the associated locked apartment
        apt_id = update_fields.get("apartment_id")
        apartment = apartment_for_update(apt_id) if apt_id else tenancy.apartment
        
        sem_id =  update_fields.get("semester_id", tenancy.semester_id) # type: ignore

        # Validate new semester - apartment combination
        self._validate_apartment_vacancy(apartment=apartment, semester_id=sem_id) # type: ignore

        # individual updates for semester and apartment
        for field, value in update_fields.items():
            setattr(tenancy, field, value)
        tenancy.full_clean()
        tenancy.save(update_fields=list(update_fields.keys()))
        return tenancy
    
    @transaction.atomic
    def delete(self) -> None:
        tenancy = self.tenancy_get_locked()
        if tenancy.total_paid > Decimal(0):
            PaymentCreateService(
                amount=tenancy.total_paid,
                transaction_type="credit",
                tenancy_id=tenancy.pk,
                initiator="system",
            ).create()
        tenancy.delete()
