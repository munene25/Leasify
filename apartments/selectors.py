from typing import Any, TYPE_CHECKING
from django.db import models
from common.domain import FilteringPolicy
from common.period import DateRange
from common.helpers import raise_not_found
from apartments.models import Apartment

if TYPE_CHECKING:
    from users.models import User

apartment_not_found = raise_not_found("apartment_id", "Apartment does not exist")


class ApartmentFilterPolicy(FilteringPolicy):
    """How each user role affects which apartments are visible to them"""

    SUPERUSER = models.Q()
    MANAGER = models.Q()
    CARETAKER = models.Q()
    TENANT = lambda user: get_listable_q() | apartment_recent_for(user)
    REGULAR = lambda user: get_listable_q()


def get_listable_q(*args) -> models.Q:
    """Needed to add *args to allow calling it with user"""
    from django.utils import timezone
    from tenancy.models import Tenancy

    r = DateRange.with_grace_period(timezone.now().date())
    return ~models.Q(
        tenancy__start_date__lte=r.end_date,
        tenancy__end_date__gte=r.start_date,
        tenancy__status__in=[Tenancy.Status.ACTIVE, Tenancy.Status.PENDING],
    )

def apartment_recent_for(user: "User") -> models.Q:
    from tenancy.selectors import tenancy_recent

    apartment_id = getattr(tenancy_recent(user), "apartment_id", None)
    return models.Q(pk=apartment_id)


def get_base_qs() -> models.QuerySet[Apartment]:
    """
    This is defined within a function to avoid prematurely evaluating the current_semester
    In essence it's important to tell at a glance whether the apartment is occupied or not.
    """
    from tenancy.selectors import get_current_tenant_prefetch

    return Apartment.objects.prefetch_related(get_current_tenant_prefetch())


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
        order_by = django_filters.OrderingFilter(fields=("unit_number", "rent"))
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

    a_filters = ApartmentFilterPolicy.for_user(user)
    apartments = get_base_qs().filter(a_filters)
    return ApartmentFilter(filters, apartments).qs


def apartment_overview(r: DateRange):
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
    popularity = apartments.annotate(
        tenancies_count=models.Count(
            "tenancy",
        )
    ).order_by("-tenancies_count")
    occupied = apartments.filter(tenancy__start_date__lte=r.start_date, tenancy__end_date__gte=r.end_date).count()

    return {
        "total_apartments": total_apartments,
        "rentable": rentable,
        "occupied": occupied,
        "least_popular": getattr(popularity.last(), "apartment_name", None),
        "most_popular": getattr(popularity.first(), "apartment_name", None),
        "average_rent": aggregates["rent__avg"],
        "min_rent": aggregates["rent__min"],
        "max_rent": aggregates["rent__max"],
        "gross_expected_income": aggregates["rent__sum"],
    }


@apartment_not_found
def apartment_get_for(*, user: "User", apartment_id: int):
    """Filter the apartment based on the type of user first before fetch"""
    a_filters = ApartmentFilterPolicy.for_user(user)
    return get_base_qs().filter(a_filters).get(pk=apartment_id)


@apartment_not_found
def apartment_lock(apartment_id: int) -> Apartment:
    """With all the new changes, it is better to lock the apartment as there are no safeguards enforced at the db"""
    return Apartment.objects.select_for_update().get(pk=apartment_id)
