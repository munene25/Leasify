from datetime import timezone, date
from typing import Any
from decimal import Decimal
from django.db import transaction
from django.contrib.auth.models import Group
from rest_framework.exceptions import ValidationError
from tenancy.models import Tenancy
from semesters import selectors as sem_selectors
from users import selectors as user_selectors
from payments.services import PaymentCreateService


class TenancyService:
    def __init__(self, tenancy: Tenancy | None = None):
        self.EDITABLE_FIELDS = {"semester_id", "apartment_id"}
        self.tenancy = tenancy

    def _tenancy_get_validated(self) -> Tenancy:
        if not self.tenancy:
            raise ValidationError({"tenancy_id": "tenancy not set"})
        return self.tenancy

    def _validate_semester_dates(self, semester_id: int) -> None:
        selected_semester = sem_selectors.semester_get_by_id(semester_id)
        now = date.today()
        if now > selected_semester.end_date:
            err = "Invalid semester. Please select a semester that has not yet concluded"
            raise ValidationError({"semester_id": [err]})

    def _validate_user_existing_tenancy(self, *, semester_id: int, user_id: int) -> None:
        if Tenancy.objects.filter(user_id=user_id, semester_id=semester_id).exists():
            raise ValidationError(
                {"user_id": ["User already has an active tenancy in selected semester"]}
            )
        
    def _validate_apartment_vacancy(self, *, apartment_id: int, semester_id: int) -> None:
        if Tenancy.objects.filter(
            apartment_id=apartment_id, semester_id=semester_id
        ).exists():
            raise ValidationError({"apartment_id": ["Aparment is not available in selected semester"]})

    @transaction.atomic
    def create(self, **kwargs : Any) -> Tenancy:
        """
        Params: "user_id", "semester_id", "apartment_id"
        Requires primary key related fields for 'user', 'semester', 'apartment'.
        Serializer handles object existence validation.
        """
        semester_id = kwargs["semester_id"]
        user_id = kwargs["user_id"]
        apartment_id = kwargs["apartment_id"]
        # Validation moved to serializers so all id's are verified
        self._validate_semester_dates(semester_id)
        self._validate_user_existing_tenancy(semester_id=semester_id, user_id=user_id)
        self._validate_apartment_vacancy(
            semester_id=semester_id, apartment_id=apartment_id
        )
        # Create tenancy
        tenancy = Tenancy.objects.create(
            user_id=user_id,
            apartment_id=apartment_id,
            semester_id=semester_id,
            total_paid=Decimal("0.00"),
        )
        # fetch user and add user to group if not already added
        # Can't avoid refetching the user here.
        user = user_selectors.user_get_by_id(user_id)
        tenancy_group, _ = Group.objects.get_or_create(name="Tenant")
        user.groups.add(tenancy_group)
        return tenancy

    @transaction.atomic
    def update(self, **kwargs: int ) -> Tenancy:
        '''
        Params: 'apartment_id', 'semester_id'.
        Requires 'semester' and 'apartment' as select related on tenancy.
        Need a locked row with instantiation.
        '''
        tenancy = self._tenancy_get_validated()
        update_fields = {
            k: v
            for k, v in kwargs.items()
            if k in self.EDITABLE_FIELDS and getattr(tenancy, k) != v
        }
        # Short circuit
        if not update_fields:
            return tenancy
        
        # lock and reload the tenancy row for updates
        # might move to row locking to the view
        # should lock related apt
        tenancy = Tenancy.objects.select_for_update().get(pk=tenancy.pk)

        apt_id = update_fields.get("apartment_id", getattr(tenancy, "apartment_id"))
        sem_id = update_fields.get("semester_id", getattr(tenancy, "semester_id"))

        # Validate new semester - apartment combination
        self._validate_apartment_vacancy(apartment_id=apt_id, semester_id=sem_id)

        # individual updates for semester and apartment
        if "semester_id" in update_fields:
            self._validate_semester_dates(sem_id)
            setattr(tenancy, "semester_id", sem_id)
        if "apartment_id" in update_fields:
            setattr(tenancy, "apartment_id", apt_id)

        tenancy.save(update_fields=list(update_fields.keys()))
        return tenancy
    
    @transaction.atomic
    def delete(self) -> None:
        tenancy = self._tenancy_get_validated()
        # Credit all payments
        PaymentCreateService(
            amount=tenancy.total_paid,
            transaction_type="credit",
            tenancy_id=tenancy.pk,
            initiator="system",
        ).create()
        # Delete
        tenancy.delete()
