from typing import Any, TYPE_CHECKING
from django.db import models
from django.db.models.query import QuerySet

from common.domain import FilteringPolicy
from common.helpers import raise_not_found

from apartments.models import Apartment
from tenancy.selectors import CURRENT_TENANT
from tenancy.choices import TenancyStatus, ACTIVE_OR_DEFAULTING

if TYPE_CHECKING:
    from users.models import User

apartment_not_found = raise_not_found("apartment_id", "Apartment does not exist")

BASE_QS = Apartment.objects.prefetch_related(CURRENT_TENANT)

LISTABLE = models.Q(rentable=True) & models.Q(tenancy__isnull=True) | models.Q(tenancy__status=TenancyStatus.TERMINATED)


class ApartmentFilterPolicy(FilteringPolicy):
    """How each user role affects which apartments are visible to them"""

    SUPERUSER = models.Q()
    MANAGER = models.Q()
    CARETAKER = models.Q()
    TENANT = LISTABLE
    REGULAR = LISTABLE


def apartment_list_for(*, user: "User", filters: dict[str, Any] | None = None) -> QuerySet[Apartment]:
    """
    Fetches apartment list visible for the requesting user.
    filters based on fields: search and rentable.
    rent can be filtered against rent_max and rent_min as well.
    prefetch is necessary in the list view to be able to tell if it's occupied.
    """

    import django_filters

    class ApartmentFilter(django_filters.FilterSet):
        order_by = django_filters.OrderingFilter(fields=("rent"))
        rent = django_filters.RangeFilter(field_name="rent")

        class Meta:
            model = Apartment
            fields = ("rentable", "block", "unit_number", "floor", "wing")

    a_filters = ApartmentFilterPolicy.for_user(user)
    apartments = BASE_QS.filter(a_filters)
    return ApartmentFilter(filters, apartments).qs


def apartment_get_overview() -> dict[str, int | float | str | None]:
    """Return an overview of apartment statistics."""
    from django.db.models import Avg, Count, Min, Max, Sum, Q
    from decimal import Decimal

    apartments = Apartment.objects.all()

    aggregates = apartments.aggregate(
        average_rent=Avg("rent"),
        min_rent=Min("rent"),
        max_rent=Max("rent"),
        gross_expected=Sum("rent", filter=Q(rentable=True), default=Decimal(0.00)),
    )

    popularity = apartments.annotate(tenancy_count=Count("tenancy", distinct=True)).order_by("-tenancy_count", "id")

    return {
        "total_apartments": apartments.count(),
        "rentable": apartments.filter(rentable=True).count(),
        "occupied": (apartments.filter(tenancy__status__in=ACTIVE_OR_DEFAULTING).distinct().count()),
        "most_popular": getattr(popularity.first(), "name", None),
        "least_popular": getattr(popularity.last(), "name", None),
        **aggregates,
    }


@apartment_not_found
def apartment_get_for(*, user: "User", apartment_id: int):
    """Filter the apartment based on the type of user first before fetch"""
    a_filters = ApartmentFilterPolicy.for_user(user)
    return BASE_QS.filter(a_filters).get(pk=apartment_id)