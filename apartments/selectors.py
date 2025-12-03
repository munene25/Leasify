from django.db import models
from rest_framework.exceptions import NotFound
from .models import Apartment
from tenancy.models import Tenancy
from tenancy import selectors as tenancy_selectors
from semesters import selectors as semester_selectors
from semesters.models import Semester


def apartment_overview(semester_id: int):
    """
    Return an overview of apartment occupancy for a the current semester:
    total, occupied, and vacant counts.
    """
    apartments = Apartment.objects.all()
    total_apartments = apartments.count()
    available = apartment_available_units(semester_id=semester_id).count()

    return {
        "total_apartments": total_apartments,
        "available": available,
        "vacant": total_apartments - available,
    }


def apartment_list():
    return Apartment.objects.all()


def apartment_get_for_update(apartment_id: int):
    try:
        return Apartment.objects.select_for_update().get(pk=apartment_id)
    except Apartment.DoesNotExist:
        raise NotFound({"apartment_id": f"Apartment {apartment_id} not found"})


def apartment_get_by_id(apartment_id: int):
    try:
        return Apartment.objects.get(pk=apartment_id)
    except Apartment.DoesNotExist:
        raise NotFound({"apartment_id": f"Apartment {apartment_id} not found"})


def apartment_available_units(semester_id: int):
    return Apartment.objects.filter(rentable=True).exclude(
        tenancy__semester_id=semester_id
    )


def apartment_occupancy_in_semester(*, apartment_id: int, semester_id: int):
    try:
        return Apartment.objects.annotate(
            occupancy_count=models.Count(
                "tenancy", filter=models.Q(tenancy__semester_id=semester_id)
            )
        ).get(id=apartment_id)
    except Apartment.DoesNotExist:
        raise NotFound({"apartment_id": [f"Apartment {apartment_id} not found"]})
    except Semester.DoesNotExist:
        raise NotFound({"semester_id": [f"Semester {semester_id} not found"]})
