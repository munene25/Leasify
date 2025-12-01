from datetime import timezone, datetime
from decimal import Decimal
from django.db import transaction
from django.contrib.auth.models import Group
from rest_framework.exceptions import ValidationError
from tenancy.models import Tenancy
from tenancy import selectors as tenancy_selectors
from semesters import selectors as sem_selectors
from apartments import selectors as apt_selectors
from users import selectors as user_selectors
from payments.services import PaymentCreateService

class TenancyService:
    def __init__(self, tenancy_id: int | None = None):
        self.EDITABLE_FIELDS = {"semester", "apartment"}
        self.tenancy = (
            tenancy_selectors.tenancy_get_by_id(tenancy_id) if tenancy_id else None
        )

    def _validate_semester_dates(self, semester_id: int) -> None:
        selected_semester = sem_selectors.semester_get_by_id(semester_id)
        now = datetime.now(tz=timezone.utc)
        if now > selected_semester.end_date:
            err = (
                "Invalid semester. Please select a semester that has not yet concluded"
            )
            raise ValidationError({"semester_id": [err]})

    def _validate_user_existing_tenancy(
        self, *, semester_id: int, user_id: int
    ) -> None:
        # consider collapsing both into a single check with **kwargs = user_id, apt_id, semeester_id
        if Tenancy.objects.filter(user_id=user_id, semester_id=semester_id).exists():
            raise ValidationError(
                {"user_id": ["User already has an active tenancy in selected semester"]}
            )

    def _validate_apartment_vacancy(
        self, *, apartment_id: int, semester_id: int
    ) -> None:
        if Tenancy.objects.filter(
            apartment_id=apartment_id, semester_id=semester_id
        ).exists():
            raise ValidationError(
                {"apartment_id": ["Aparment is not available in selected semester"]}
            )

    @transaction.atomic
    def create(self, user_id: int, semester_id: int, apartment_id: int) -> Tenancy:
        # Validate the user and apt actually exist
        user = user_selectors.user_get_by_id(user_id)
        apt_selectors.apartment_get_by_id(apartment_id)

        self._validate_semester_dates(semester_id)
        self._validate_user_existing_tenancy(semester_id=semester_id, user_id=user_id)
        self._validate_apartment_vacancy(semester_id=semester_id, apartment_id=apartment_id)

        # Create tenancy and add to group
        tenancy = Tenancy.objects.create(
            user_id=user_id,
            apartment_id=apartment_id,
            semester_id=semester_id,
            total_paid=Decimal("0.00"),
        )
        tenancy_group, _ = Group.objects.get_or_create(name="Tenant")
        user.groups.add(tenancy_group)
        return tenancy

    def update(self, **kwargs: dict[str, int]):
        if not self.tenancy:
            raise ValidationError({"tenancy_id":"tenancy not set"})
        # TODO: Need to validate semester and apt as well?
        update_fields: dict = {
            k: v
            for k, v in kwargs.items()
            # importatnt note here, the expected values of the kwargs(dict) are id's
            # Selecting related semester and apt already avoids N + 1
            if k in self.EDITABLE_FIELDS and getattr(self.tenancy, k).pk != v
        }
        if not update_fields:
            return self.tenancy

        # No need to check occurence of fields coz there is only two editable fields
        apt_id = update_fields.get("apartment", getattr(self.tenancy, "apartment_id"))
        sem_id = update_fields.get("semester", getattr(self.tenancy, "semester_id"))
        # Validate new semester - apartment combination
        self._validate_apartment_vacancy(apartment_id=apt_id, semester_id=sem_id)

        # individual updates for semester and apartment
        if "semester" in update_fields:
            self._validate_semester_dates(sem_id)
            setattr(self.tenancy, "semester_id", sem_id)
        if "apartment" in update_fields:
            setattr(self.tenancy, "apartment_id", apt_id)

        self.tenancy.save(update_fields=list(update_fields.keys()))
        return self.tenancy


    def delete(self):
        if not self.tenancy:
            raise ValidationError({"tenancy_id":"tenancy not set"})

        # Credit all payments
        PaymentCreateService(
            amount=self.tenancy.total_paid,
            transaction_type="credit",
            tenancy_id=self.tenancy.pk,
            initiator="system",
        ).create()

        self.tenancy.delete()