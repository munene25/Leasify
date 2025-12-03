from .models import Semester
from rest_framework.exceptions import NotFound
from datetime import date

def semester_list():
    return Semester.objects.all()


def semester_get_by_name(semester_name: str):
    """
    Return a Semester instance filtered by the semester_name else 404
    """
    try:
        return Semester.objects.get(name=semester_name)
    except Semester.DoesNotExist:
        raise NotFound({"semester_id": f"Semester {semester_name} not found"})


def semester_get_by_id(semester_id):
    try:
        return Semester.objects.get(pk=semester_id)
    except Semester.DoesNotExist:
        raise NotFound({"semester_id": f"Semester {semester_id} not found"})

def semesters_get_all_from_today():
    return Semester.objects.filter(end_date__gte=date.today()).only("id")

def semester_current():
   try: 
        return Semester.objects.get(
            start_date__lte=date.today(), end_date__gte=date.today()
        )
   except Semester.DoesNotExist:
       raise NotFound({"current_semester": [f"Semester not found, please create a semester for this time period"]})
