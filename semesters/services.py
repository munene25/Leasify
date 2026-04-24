from typing import Any
from datetime import date
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Semester
from . import selectors


@transaction.atomic
def semester_create(
    *,
    start_date: date,
    end_date: date,
    off_season: bool = False,
    alt_name: str | None = None,
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
        alt_name=alt_name,
        start_date=start_date,
        end_date=end_date,
        off_season=off_season,
    )
    semester.full_clean()
    semester.save()
    return semester


@transaction.atomic
def semester_update(semester: Semester, **kwargs: Any) -> Semester:
    """
    params must be in editable fields
    :param kwargs: alt_name: str, start_date: date, end_date: date.
    :type kwargs: dict[str, int | date]
    :returns: The updated Semester object.
    :rtype: Semester
    """
    editable_fields = {"alt_name", "start_date", "end_date", "off_season"}
    update_fields = {k: v for k, v in kwargs.items() if k in editable_fields and getattr(semester, k) != v}

    if not update_fields:
        return semester

    for field, value in update_fields.items():
        setattr(semester, field, value)
    semester.full_clean()
    semester.save(update_fields=list(update_fields.keys()))
    return semester


@transaction.atomic
def semester_delete(semester: Semester):
    if getattr(semester, "tenancy_set").exists():
        raise ValidationError(
            {
                "semester_id": "Cannot delete a semester with associated tenants. Please remove tenancies before continuing"
            }
        )
    semester.delete()