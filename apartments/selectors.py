from typing import Any, Callable, TYPE_CHECKING
from django.db import models
from apartments.models import Apartment
from semesters.models import Semester
from rest_framework.exceptions import NotFound
from common.helpers import raise_not_found
from users.models import User
from common.domain import RoleBasedExclusions
from tenancy.selectors import tenancy_current

if TYPE_CHECKING:
    from tenancy.models import Tenancy

# wrapper to raise not found for each id
apartment_not_found = raise_not_found("apartment_id", "Apartment does not exist")


class ApartmentExclusions(RoleBasedExclusions):
    """How each user role affects which apartments are visible to them"""

    SUPERUSER = models.Q()
    MANAGER = models.Q()
    CARETAKER = models.Q()
    TENANT = models.Q(rentable=False)
    GENERAL = TENANT

# decoupled in order to use modularly eg. in admin
tenancy_prefetch = lambda: models.Prefetch("tenancy_set", tenancy_current(), to_attr="current_tenants")

def get_base_qs() -> models.QuerySet[Apartment]:
    """
    This is defined within a function to avoid prematurely evaluating the current_semester
    In essence it's important to tell at a glance whether the apartment is occupied or not.    
    """

    return Apartment.objects.prefetch_related(tenancy_prefetch())


def apartment_list_for(*, user: User, filters: dict[str, Any] | None = None):
    """
    Fetches apartment list visible for the requesting user.
    filters based on fields: search and rentable.
    rent can be filtered against rent_max and rent_min as well.
    prefetch is necessary in the list view to be able to tell if it's occupied.
    """

    import django_filters
    from decimal import Decimal

    class ApartmentFilter(django_filters.FilterSet):
        order_by=django_filters.OrderingFilter(fields=("unit_number", "rent"))
        search = django_filters.CharFilter(method="search_fields")
        rent = django_filters.RangeFilter(field_name="rent")

        class Meta:
            model = Apartment
            fields = ("rentable",)

        def search_fields(self, queryset, name, value):
            query = models.Q(block__icontains=value)
            if value.isdigit():
                try:
                    query |= models.Q(unit_number=int(value)) | models.Q(rent=Decimal(value))
                except ValueError:
                    pass
            return queryset.filter(query)

    exclusions = ApartmentExclusions.for_user(user)
    apartments = get_base_qs().exclude(exclusions)
    return ApartmentFilter(filters, apartments).qs


def apartment_overview(semester: Semester):
    """
    Return an overview of apartments occupancy for the selected semester:
    total, occupied, and vacant counts.
    """

    apartments = Apartment.objects.all()
    aggregates = apartments.aggregate(
        models.Avg("rent"),
        models.Max("rent"),
        models.Min("rent"),
        models.Sum("rent"),
    )
    total_apartments = apartments.count()
    rentable = apartments.filter(rentable=True).count()
    occupied = apartments.filter(tenancy__semester_id=semester.pk).count()

    return {
        "total_apartments": total_apartments,
        "rentable": rentable,
        "occupied": occupied,
        "average_rent": aggregates["rent__avg"],
        "min_rent": aggregates["rent__min"],
        "max_rent": aggregates["rent__max"],
        "expected_income": aggregates["rent__sum"],
    }


@apartment_not_found
def apartment_for_update(apartment_id: int):
    """Lock the apartment during payment processing"""
    return Apartment.objects.select_for_update().get(pk=apartment_id)


@apartment_not_found
def apartment_get_for(*, user: User, apartment_id: int):
    """Filter the apartment based on the type of user first before fetch"""
    exclusions = ApartmentExclusions.for_user(user)
    return get_base_qs().exclude(exclusions).get(pk=apartment_id)


def apartment_available_units(semester_id: int):
    return Apartment.objects.filter(rentable=True).exclude(tenancy__semester_id=semester_id)
