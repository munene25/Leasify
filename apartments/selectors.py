from typing import Any
from django.db import models
from apartments.models import Apartment
from semesters.models import Semester
from rest_framework.exceptions import NotFound
from common.helpers import raise_not_found
from users.models import User
from common.domain import RoleBasedExclusions


# wrapper to raise not found for each id
apartment_not_found = raise_not_found("apartment_id", "Apartment does not exist")


class ApartmentExclusions(RoleBasedExclusions):
    """How each user role affects which apartments are visible to them"""

    SUPERUSER = models.Q()
    MANAGER = models.Q()
    CARETAKER = models.Q()
    TENANT = models.Q(rentable=False)
    GENERAL = TENANT


def get_base_qs_with_current_tenant_prefetch() -> models.QuerySet[Apartment]:
    """
    This is defined within a function to avoid prematurely evaluating the current_semester
    In essence it's important to tell at a glance whether the apartment is occupied or not.
    It is also important to decouple the semester existing or not in order to get the current tenant.
    """

    from semesters.selectors import semester_current
    from tenancy.models import Tenancy

    try:
        sem = semester_current()
        tenancy = Tenancy.objects.select_related("user").filter(semester_id=sem.pk)
    except NotFound:
        tenancy = Tenancy.objects.none()
        
    return Apartment.objects.prefetch_related(models.Prefetch("tenancy_set", tenancy, to_attr="current_tenants"))


def apartment_list_for(*, user: User, filters: dict[str, Any] | None = None):
    """
    Fetches apartment list visible for the requesting user.
    filters based on fields: search and rentable.
    rent can be filtered against rent_max and rent_min as well
    prefetch is necessary in the list view to be able to tell if it's occupied.
    """

    import django_filters
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
                try:
                    query |= models.Q(unit_number=int(value)) | models.Q(rent=Decimal(value))
                except ValueError:
                    pass
            return queryset.filter(query)

    exclusions = ApartmentExclusions.for_user(user)
    apartments = get_base_qs_with_current_tenant_prefetch().exclude(exclusions)
    return ApartmentFilter(filters, apartments).qs


def apartment_overview(semester: Semester):
    """
    Return an overview of apartments occupancy for the selected semester:
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
    """Lock the apartment during payment processing"""
    return Apartment.objects.select_for_update().get(pk=apartment_id)


@apartment_not_found
def apartment_get_for(*, user: User, apartment_id: int):
    """Filter the apartment based on the type of user first before fetch"""
    exclusions = ApartmentExclusions.for_user(user)
    return get_base_qs_with_current_tenant_prefetch.exclude(exclusions).get(pk=apartment_id)


def apartment_available_units(semester_id: int):
    return Apartment.objects.filter(rentable=True).exclude(tenancy__semester_id=semester_id)
