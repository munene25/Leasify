from datetime import date
from django.core.cache import cache
from django.utils import timezone
from django.db.models import QuerySet
from semesters.models import Semester, GRACE_PERIOD
from common.helpers import raise_not_found



def semester_within_grace_period() -> list[int]:
    """
    This is a really crucial addition to the way booking works.
    Take for example a user who is a tenant during the first semester.
    The apartment is taken of listings automatically, but the tenant wants to pay for this apartment again.
    We need a way to get a way to give grace to the user to allow them to see and pay for their apartment.
    This selector during the beginning of the first semester, will yield the previous semester.
    But once grace period is over, it will only show the current semester
    
    That said, while filtering apartments based on the semester_id, it will allow the user to continuously 
    pay for their apartment for up to the length of the grace period even after semester ends.
    """
    now = timezone.now().date()
    extension = (now - GRACE_PERIOD)
    semesters_within_range = Semester.objects.order_by("-start_date").filter(start_date__lte=now, end_date__gte=extension).values_list("pk", flat=True)
    return list(semesters_within_range)

def semester_list() -> QuerySet:
    return Semester.objects.all()

@raise_not_found("semester_id", "Semester not found")
def semester_get(semester_id: int)-> Semester:
    return Semester.objects.get(pk=semester_id)

@raise_not_found("current_semester", "No current semester has been set for this time period")
def semester_current() -> Semester:
    """This has to be cached due to the mulitple number of times it will be called"""

    cache_key = "semester:semester_current"
    if cached := cache.get(cache_key):
        return cached
    
    now = timezone.now()
    semester = Semester.objects.get(start_date__lte=now, end_date__gte=now)
    timeout = max(1, int((semester.end_date - now.date()).total_seconds()))
    cache.set(cache_key, semester, timeout=timeout)
    return semester
