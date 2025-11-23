from datetime import date
from rest_framework.exceptions import ValidationError
from django.db import transaction
from semesters import selectors as semester_selectors
from apartments import selectors as apartment_selectors
from tenancy.selectors import tenancy_get_by_id
from apartments.services import ApartmentUpdateService


class TenancyUpdateService:
    """
    Fields updated: apartment_id, semester_id
    If apartment changes, old apartment is made available again, and new one is made unavailable.
    If semester changes, ensures no duplicate tenancy for that user in the same semester.
    """

    def __init__(self, tenancy_id, **kwargs):
        self.tenancy_id = tenancy_id
        self.apartment_id = kwargs.get("apartment_id")
        self.semester_id = kwargs.get("semester_id")
        self.update_fields = [k for k, v in kwargs.items() if v is not None]

    def _get_tenancy(self):
        self.tenancy = tenancy_get_by_id(tenancy_id=self.tenancy_id)

    def _resolve_apartment_semester_ids(self):
        self.new_apt_id = (
            self.apartment_id
            if "apartment_id" in self.update_fields
            else self.tenancy.apartment_id
        )
        self.new_semester_id = (
            self.semester_id
            if "semester_id" in self.update_fields
            else self.tenancy.semester_id
        )

    def _verify_vacancy(self):
        apt = apartment_selectors.apartment_occupancy_in_semester(
            apartment_id=self.new_apt_id, semester_id=self.new_semester_id
        )
        if apt.available:
            return
        # If the apartment  is not available and occupied in that semester, raise error
        if apt.occupancy_count != 0:
            err = f"Apartment {apt.id} is occupied in that period"
            raise ValidationError({"apartment_id": [err]})

    def _update_new_apartment(self):
        ApartmentUpdateService(apartment_id=self.new_apt_id, available=False).update()
        self.tenancy.apartment_id = self.new_apt_id

    def _update_old_apartment(self):
        try:
            ApartmentUpdateService(
                apartment_id=self.tenancy.apartment_id, available=True
            ).update()
        except ValidationError:
            pass

    def _update_semester(self):
        new_sem = semester_selectors.semester_get_by_id(
            semester_id=self.new_semester_id
        )
        if new_sem.end_date <= date.today():
            err = "Cannot move tenancy to a past semester."
            raise ValidationError({"semester_id": [err]})
        self.tenancy.semester_id = self.new_semester_id

    @transaction.atomic
    def update(self):
        self._get_tenancy()
        self._resolve_apartment_semester_ids()
        if (
            self.new_apt_id == self.tenancy.apartment_id
            and self.new_semester_id == self.tenancy.semester_id
        ):
            return self.tenancy
        self._verify_vacancy()
        if "apartment_id" in self.update_fields:
            self._update_old_apartment()
            self._update_new_apartment()
        if "semester_id" in self.update_fields:
            self._update_semester()
        self.tenancy.save(update_fields=self.update_fields)
        return self.tenancy
