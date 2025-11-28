from typing import Any
from datetime import date
from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError
from apartments.models import Apartment
from .models import Semester
from . import selectors

DEFAULT_RENT = Decimal("16000.00")
DEFAULT_HOLIDAY_RENT = Decimal("12000.00")

class SemesterService:
    def __init__(self, semester_id: int | None = None) -> None:
        self.semester = selectors.semester_get_by_id(semester_id=semester_id) if semester_id else None
        self.EDITABLE_FIELDS = {"name", "start_date", "end_date", "off_season", "semester_rent"}


    def _validate_name(self, name: str) -> None:
        invalid = ValidationError({"name": ["Invalid name format. Use 'MMM-MMM-YYYY'"]})
        if len(name) != 12:
            raise invalid
        try:
            start, end, year = name.split("-")
        except ValueError:
            raise invalid
        if not (start.isalpha() and end.isalpha() and year.isdigit()):
            raise invalid

    def _validate_dates(self, start_date: date, end_date: date) -> None:
        if not all(isinstance(v, date) for v in (start_date, end_date)):
            err = "Invalid date format"
            raise ValidationError({"start_date": [err], "end_date": [err]})
        if end_date <= start_date:
            raise ValidationError({"end_date": ["start date cannot appear on or before end date"]})

    def _validate_rent(self, rent: int | Decimal) -> None:
        if not isinstance(rent, (int, Decimal)):
            tname = type(rent).__name__
            raise ValidationError({"rent": [f"Values of type '{tname}' are not allowed"]})

    def _get_default_rent(self, semester: Semester) -> Decimal:
        return DEFAULT_HOLIDAY_RENT if getattr(semester, "off_season", True) else DEFAULT_RENT

    @transaction.atomic
    def create(
        self,
        *,
        name: str,
        start_date: date,
        end_date: date,
        off_season: bool,
        rent: int | Decimal | None = None,
    ) -> Semester:
        """Create expects 'rent' 'start date' and 'end date' and 'off_season' values"""

        # Clean values immediately and raise if error
        self._validate_name(name)
        self._validate_dates(start_date, end_date)
        semester = Semester(
            name=name,
            start_date=start_date,
            end_date=end_date,
            off_season=off_season,
        )

        semester.rent = (
            Decimal(rent)
            if rent
            else self._get_default_rent(semester)
        )
        semester.save()
        return semester

    @transaction.atomic
    def update(self, **kwargs: Any) -> Semester:
        """ name, start and end date, rent, and a flag for changing all apartment rents in that semester as well if changing the rent"""
        if not self.semester:
            raise ValidationError({"semester_id": ["Semester not provided"]})

        update_fields = {
            k: v for k, v in kwargs.items()
            if k in self.EDITABLE_FIELDS and getattr(self.semester, k) != v
        }

        if "name" in update_fields:
            self._validate_name(update_fields["name"])
        if "start_date" in update_fields or "end_date" in update_fields:
            s = update_fields.get("start_date", self.semester.start_date)
            e = update_fields.get("end_date", self.semester.end_date)
            self._validate_dates(s, e)
        if "rent" in update_fields:
            self._validate_rent(update_fields["rent"])
            if kwargs.get("update_apts"):
                Apartment.objects.exclude(rentable=False).update(
                    rent=update_fields["rent"]
                )

        for field, value in update_fields.items():
            setattr(self.semester, field, value)
        self.semester.full_clean()
        self.semester.save(update_fields=list(update_fields.keys()))
        return self.semester
