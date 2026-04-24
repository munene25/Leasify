from django.core.cache import cache
from semesters.models import Semester
from rest_framework.exceptions import NotFound
from django.utils import timezone
from django.db.models import QuerySet
from common.helpers import raise_not_found



def semester_list():
    return Semester.objects.all()

def semester_for_update(semester_id: int) -> Semester:
    """
    Return a Semester instance filtered by the semester_name else 404
    """
    try:
        return Semester.objects.select_for_update().prefetch_related("tenancy_set").get(pk=semester_id)
    except Semester.DoesNotExist:
        raise NotFound({"semester_id": f"Semester {semester_id} not found"})


def semester_get_by_id(semester_id)-> Semester:
    try:
        return Semester.objects.get(pk=semester_id)
    except Semester.DoesNotExist:
        raise NotFound({"semester_id": f"Semester {semester_id} not found"})

def semesters_get_all_from_today()-> QuerySet:
    return Semester.objects.filter(end_date__gte=timezone.now()).only("id")


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
