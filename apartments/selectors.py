from typing import Any
from django.db import models
from rest_framework.exceptions import NotFound
from apartments.models import Apartment
from semesters.models import Semester
from common.helpers import raise_not_found
from users.models import User
from common.domain import RoleBasedExclusions

# wrapper to raise not found for each id
apartment_not_found = raise_not_found("apartment_id", "Apartment does not exist")

BASE_PREFETCH_QS = Apartment.objects.prefetch_related("tenancy_set")


class ApartmentExclusions(RoleBasedExclusions):
    """How each user role affects which apartments are visible to them"""

    SUPERUSER = models.Q()
    MANAGER = models.Q()
    CARETAKER = models.Q()
    TENANT = models.Q(rentable=False)
    GENERAL = TENANT


def apartment_list_for(*, user: User, filters: dict[str, Any] | None = None):
    """
    Fetches apartment list visible for the requesting user.
    filters based on fields: search and rentable.
    """
    import django_filters
    from django.db.models.functions import Cast
    from decimal import Decimal

    class ApartmentFilter(django_filters.FilterSet):
        search = django_filters.CharFilter(method="search_fields")
        rent = django_filters.RangeFilter(field_name="rent")

        class Meta:
            model = Apartment
            fields = ("rentable",)

        def search_fields(self, queryset, name, value):
            query = models.Q(block__icontains=value)
            if value.isdigit():
                query |= models.Q(unit_number=int(value)) | models.Q(rent=Decimal(value))
            return queryset.filter(query)

    exclusions = ApartmentExclusions.for_user(user)
    apartments = BASE_PREFETCH_QS.exclude(exclusions)
    return ApartmentFilter(filters, apartments).qs


def apartment_overview(semester: Semester):
    """
    Return an overview of apartments occupancy for the current semester:
    total, occupied, and vacant counts.
    """
    
    apartments = Apartment.objects.all()
    total_apartments = apartments.count()
    available = apartment_available_units(semester_id=semester.pk).count()

    return {
        "total_apartments": total_apartments,
        "rentable": available,
        "vacant": total_apartments - available,
    }


@apartment_not_found
def apartment_for_update(apartment_id: int):
    return Apartment.objects.select_for_update().get(pk=apartment_id)


@apartment_not_found
def apartment_get_for(*, user: User, apartment_id: int):
    exclusions = ApartmentExclusions.for_user(user)
    return Apartment.objects.exclude(exclusions).get(pk=apartment_id)


def apartment_get_tenant_during(apartment_id: int, semester: Semester | None = None):
    from semesters.selectors import semester_current

    semester = semester or semester_current()
    return (
        Apartment.objects.prefetch_related("tenancy_set").get(pk=apartment_id, tenancy__semester_id=semester.pk).first()  # type: ignore
    )


def apartment_available_units(semester_id: int):
    return Apartment.objects.filter(rentable=True).exclude(tenancy__semester_id=semester_id)


def apartment_occupancy_in_semester(*, apartment_id: int, semester_id: int):
    try:
        return Apartment.objects.annotate(
            occupancy_count=models.Count("tenancy", filter=models.Q(tenancy__semester_id=semester_id))
        ).get(id=apartment_id)
    except Apartment.DoesNotExist:
        raise NotFound({"apartment_id": [f"Apartment {apartment_id} not found"]})
    except Semester.DoesNotExist:
        raise NotFound({"semester_id": [f"Semester {semester_id} not found"]})
