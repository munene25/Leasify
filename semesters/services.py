from typing import Any
from datetime import date
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Semester
from . import selectors


class SemesterService:
    def __init__(self, semester_id: int | None = None) -> None:
        self.semester_id = semester_id
        self.EDITABLE_FIELDS = (
            "alt_name",
            "start_date",
            "end_date",
            "off_season",
        )

    def _semester_get_locked(self):
        if self.semester_id is None:
            raise ValidationError({"semester_id": "Please provide a valid semester"})
        return selectors.semester_for_update(self.semester_id)

    @transaction.atomic
    def create(
        self,
        *,
        alt_name: str | None = None,
        start_date: date,
        end_date: date,
        off_season: bool = False,
    ) -> Semester:
        """
        :param alt_name: semester's alternative name for recordkeeping
        :type alt_name: str
        :param start_date: semester start date
        :type start_date: date
        :param end_date: semester end date
        :type end_date: date
        :param off_season: marker to determine whether the semester falls in a holiday(off) season
        :type off_season: bool
        :return: Created semester object
        :rtype: Semester
        """
        semester = Semester(
            alt_name= alt_name,
            start_date=start_date,
            end_date=end_date,
            off_season=off_season,
        )
        semester.full_clean()
        semester.save()
        return semester

    @transaction.atomic
    def update(self, **kwargs: Any) -> Semester:
        """
        params must be in editable fields
        :param kwargs: alt_name: str, start_date: date, end_date: date.
        :type kwargs: dict[str, int | date]
        :returns: The updated Semester object.
        :rtype: Semester
        """
        semester = self._semester_get_locked()
        update_fields = {
            k: v
            for k, v in kwargs.items()
            if k in self.EDITABLE_FIELDS and getattr(semester, k) != v
        }
        
        if not update_fields:
            return semester
        
        for field, value in update_fields.items():
            setattr(semester, field, value)
        semester.full_clean()
        semester.save(update_fields=list(update_fields.keys()))
        return semester

    @transaction.atomic
    def delete(self):
        semester = self._semester_get_locked()
        if getattr(semester, "tenancy_set").exists():
            raise ValidationError({"semester_id": "Cannot delete a semester with associated tenants. Please remove tenancies before continuing"})
        semester.delete()