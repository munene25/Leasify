from django.core.cache import cache
from .models import Semester
from rest_framework.exceptions import NotFound
from django.utils import timezone

def semester_list():
    return Semester.objects.all()

def semester_for_update(semester_id: int):
    """
    Return a Semester instance filtered by the semester_name else 404
    """
    try:
        return Semester.objects.select_for_update().prefetch_related("tenancy_set").get(pk=semester_id)
    except Semester.DoesNotExist:
        raise NotFound({"semester_id": f"Semester {semester_id} not found"})


def semester_get_by_id(semester_id):
    try:
        return Semester.objects.get(pk=semester_id)
    except Semester.DoesNotExist:
        raise NotFound({"semester_id": f"Semester {semester_id} not found"})

def semesters_get_all_from_today():
    return Semester.objects.filter(end_date__gte=timezone.localdate()).only("id")

def semester_current():
    cache_key = "semester:semester_current"
    if semester := cache.get(cache_key):
       return semester
    try: 
        semester = Semester.objects.get(start_date__lte=timezone.localdate(), end_date__gte=timezone.localdate())
        cache.set(cache_key, semester, timeout=3600)
        return semester
    except Semester.DoesNotExist:
        raise NotFound({"current_semester": [f"Semester not found. Please create a semester for this time period"]})
