from django.contrib.auth.models import Group
from rest_framework.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from apartments.services import ApartmentUpdateService
from users import selectors as user_selectors
from apartments import selectors as apartment_selectors
from tenancy.models import Tenancy

class TenancyCreateService:
    def __init__(self, *, user_id: int, semester_id: int, apartment_id: int):
        self.user_id = user_id
        self.semester_id = semester_id
        self.apartment_id = apartment_id

    def _get_user(self):
        user = user_selectors.user_get_by_id(user_id=self.user_id)
        if user.tenancy_set.filter(semester_id=self.semester_id).exists():
            raise ValidationError({"user_id": ["user already has a tenancy"]})
        self.user = user

    def _validate_apartment_availability(self):
        apt = apartment_selectors.apartment_occupancy_in_semester(
            apartment_id=self.apartment_id, semester_id=self.semester_id
        )
        # If apartment is occupied in selected semester, raise error
        # No check for availability since this is mostly avoiding new tenants from creating tenancies 
        if apt.occupancy_count != 0:
            err = f"Apartment {self.apartment_id} already has a tenancy"
            raise ValidationError({"apartment_id": [err]})

    def _update_apartment(self):
        ApartmentUpdateService(
            apartment_id=self.apartment_id,
        ).update()

    def _add_user_to_tenant_group(self):
        group, _ = Group.objects.get_or_create(name="Tenant")
        self.user.groups.add(group)

    @transaction.atomic
    def create(self):
        self._get_user()
        self._validate_apartment_availability()
        self._update_apartment()
        tenant = Tenancy(
            user_id=self.user_id,
            apartment_id=self.apartment_id,
            semester_id=self.semester_id,
            total_paid=Decimal("0.00"),
        )
        # tenant.full_clean()
        tenant.save()
        self._add_user_to_tenant_group()
        return tenant