from typing import Any, TYPE_CHECKING
from django.db import models
from common.domain import FilteringPolicy
from common.period import DateRange
from common.helpers import raise_not_found
from apartments.models import Apartment
from tenancy.selectors import CURRENT_TENANT
from tenancy.choices import TenancyStatus, ACTIVE_RESERVED_OR_DEFAULTING

if TYPE_CHECKING:
    from users.models import User

apartment_not_found = raise_not_found("apartment_id", "Apartment does not exist")

BASE_QS = Apartment.objects.prefetch_related(CURRENT_TENANT)

LISTABLE = (
    models.Q(rentable=True)
    & models.Q(tenancy__isnull=True)
    | models.Q(tenancy__status__in=TenancyStatus.TERMINATED)
)


class ApartmentFilterPolicy(FilteringPolicy):
    """How each user role affects which apartments are visible to them"""

    SUPERUSER = models.Q()
    MANAGER = models.Q()
    CARETAKER = models.Q()
    TENANT = LISTABLE
    REGULAR = LISTABLE


def apartment_list_for(*, user: "User", filters: dict[str, Any] | None = None):
    """
    Fetches apartment list visible for the requesting user.
    filters based on fields: search and rentable.
    rent can be filtered against rent_max and rent_min as well.
    prefetch is necessary in the list view to be able to tell if it's occupied.
    """

    import django_filters
    from decimal import Decimal

    class ApartmentFilter(django_filters.FilterSet):
        order_by = django_filters.OrderingFilter(fields=("rent"))
        search = django_filters.CharFilter(method="search_fields")
        rent = django_filters.RangeFilter(field_name="rent")

        class Meta:
            model = Apartment
            fields = ("rentable",)

        def search_fields(self, queryset, name, value):
            q = models.Q()
            if value.isdigit():
                q |= models.Q(floor=value)
                q |= models.Q(unit_number=value)
                q |= models.Q(rent=Decimal(value))
            else:
                q |= models.Q(block__icontains=value)
                q |= models.Q(wing__icontains=value)
            return queryset.filter(q)

    a_filters = ApartmentFilterPolicy.for_user(user)
    apartments = BASE_QS.filter(a_filters)
    return ApartmentFilter(filters, apartments).qs


def apartment_get_overview() -> dict[str, str|int|None]:
    """Return an overview of apartments."""

    apartments = Apartment.objects.all()
    aggregates = apartments.aggregate(
        models.Avg("rent"),
        models.Max("rent"),
        models.Min("rent"),
        models.Sum("rent"),
    )
    total_apartments = apartments.count()
    rentable = apartments.filter(rentable=True).count()
    popularity = apartments.annotate(
        tenancies_count=models.Count(
            "tenancy",
        )
    ).order_by("-tenancies_count")
    occupied = apartments.filter(tenancy__status__in=[TenancyStatus.ACTIVE, TenancyStatus.DEFAULTING]).count()

    return {
        "total_apartments": total_apartments,
        "rentable": rentable,
        "occupied": occupied,
        "least_popular": getattr(popularity.last(), "name", None),
        "most_popular": getattr(popularity.first(), "name", None),
        "average_rent": aggregates["rent__avg"],
        "min_rent": aggregates["rent__min"],
        "max_rent": aggregates["rent__max"],
        "gross_expected_income": aggregates["rent__sum"],
    }


@apartment_not_found
def apartment_get_for(*, user: "User", apartment_id: int):
    """Filter the apartment based on the type of user first before fetch"""
    a_filters = ApartmentFilterPolicy.for_user(user)
    return BASE_QS.filter(a_filters).get(pk=apartment_id)


@apartment_not_found
def apartment_lock(apartment_id: int) -> Apartment:
    """With all the new changes, it is better to lock the apartment as there are no safeguards enforced at the db"""
    return Apartment.objects.select_for_update().get(pk=apartment_id)
