from django.db import models
from rest_framework.exceptions import NotFound
from .models import Apartment
from tenancy.models import Tenancy
from tenancy import selectors as tenancy_selectors
from semesters import selectors as semester_selectors
from semesters.models import Semester


def apartment_overview():
    """
    Return an overview of apartment occupancy for a given semester:
    total, occupied, and vacant counts.
    """
    apartments = Apartment.objects.all()
    total_apartments = apartments.count()
    available = apartments.filter(available=True).count()
    return {
        "total_apartments": total_apartments,
        "available": available,
        "vacant": total_apartments - available,
    }


def apartment_list():
    return Apartment.objects.all()


def apartment_get_by_id(*, apartment_id: int):
    try:
        return Apartment.objects.get(pk=apartment_id)
    except Apartment.DoesNotExist:
        raise NotFound({"apartment_id": f"Apartment {apartment_id} not found"})


def apartment_with_tenancies_from_today(*, apartment_id: int):
    semesters = semester_selectors.semesters_get_all_from_today()
    prefetch = models.Prefetch(
        "tenancy_set",
        queryset=Tenancy.objects.filter(semester__in=semesters),
        to_attr="active_tenancies",
    )
    try:
        return Apartment.objects.prefetch_related(prefetch).get(id=apartment_id)
    except:
        raise NotFound({"apartment_id": [f"apartment {apartment_id} not found"]})


def apartment_occupancy_in_semester(*, apartment_id, semester_id):
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
