from typing import Any, TYPE_CHECKING
from datetime import date
from django.http.request import QueryDict
from django.db.models import Q, F, QuerySet, Prefetch
from rest_framework.exceptions import ValidationError
from tenancy.models import Tenancy
from common.helpers import raise_not_found
from common.domain import FilteringPolicy
from django.utils import timezone
from common.period import DateRange

if TYPE_CHECKING:
    from users.models import User

BASE_QS: QuerySet[Tenancy] = Tenancy.objects.select_related("user", "apartment")

tenancy_not_found = raise_not_found("tenancy_id", "Tenancy does not exist.")



class TenancyFilterPolicy(FilteringPolicy):
    """
    Superuser, manager and caretaker should be able to view all tenancies.
    Other users should be able to view tenancies belonging to them.
    """

    SUPERUSER = MANAGER = CARETAKER = Q()
    TENANT = REGULAR = lambda user: Q(user_id=user.pk)


def tenancy_list_for(user: "User", filters: QueryDict | dict[str, Any]) -> QuerySet[Tenancy]:
    """
    List tenancies based on who is requesting
    """
    import django_filters

    class TenancyFilter(django_filters.FilterSet):
        class Meta:
            model = Tenancy
            fields = ("status", )

        search = django_filters.CharFilter(method="search_fields")
        cleared = django_filters.BooleanFilter(method="is_cleared")
        period = django_filters.CharFilter(method="filter_period")

        def search_fields(self, queryset, name, value: str):
            q = Q()
            if value.isdigit():
                q |= Q(apartment__unit_number=value)
            else:
                q |= Q(apartment__block__icontains=value)
                q |= Q(user__first_name__icontains=value)
                q |= Q(user__last_name__icontains=value)
            return queryset.filter(q)

        def is_cleared(self, queryset, name, value: bool):
            f = F("apartment__rent")
            q = Q(total_paid__gte=f) if value else Q(total_paid__lt=f)
            return queryset.filter(q)

        def filter_period(self, queryset, name, value: str):
            """Example filters: period=from=2000-MAY,to=2001-JUN"""
            from common.helpers import parse_date_range
            
            try:
                range = parse_date_range(value)
                start = range["start"]
                stop = range["stop"]
            except (ValueError, IndexError, KeyError):
                raise ValidationError("Cannot parse date ranges. Format is 'period=start=YYYY-MMM,stop=YYYY-MMM'")

            return queryset.filter(end_date__gte=start, semester__start_date__lte=stop)

    t_filters = TenancyFilterPolicy.for_user(user)
    tenancies = BASE_QS.select_related("semester").filter(t_filters)
    return TenancyFilter(filters, tenancies).qs


@tenancy_not_found
def tenancy_get_for(user: "User", tenancy_id: int) -> Tenancy:
    """Will filter out the tenancies viewable only to the user based on the policy"""

    t_filters = TenancyFilterPolicy.for_user(user)
    return BASE_QS.filter(t_filters).get(pk=tenancy_id)


@tenancy_not_found
def tenancy_get(tenancy_id: int) -> Tenancy:
    """Get tenant outside of client flows"""

    return BASE_QS.get(pk=tenancy_id)


def tenancy_recent(user: "User") -> Tenancy | None:
    """
    We want to get the most recent tenancy for a user.
    This could be the user currently inhabiting the house.
    Or was the previous active tenant of the house within the grace period.
    This helps availing the current apartment to the active tenant in aparment filters.
    """

    range = DateRange.with_grace_period(timezone.now().date())

    return tenancy_during(range).order_by("-start_date").filter(user_id=user.pk).first()


def tenancy_during(range: DateRange) -> QuerySet[Tenancy]:
    """
    Fetch tenancies which intersect a ceratin time
    """

    if not range:
        now = timezone.now().date()
        range = DateRange.get_month_date_range(now)

    return BASE_QS.filter(start_date__lte=range.end_date, end_date__gte=range.start_date)


def tenancy_overview(r: DateRange):
    """
    This selector provides an overview of the tenancies for a given duration, including:
    - The number of tenants that are cleared and not cleared.
    - The total expected rent and total collected rent for the period.
    """
    from django.db.models import Sum, Count
    from decimal import Decimal

    current_tenancies = tenancy_during(r)
    duration = r.duration_months

    previous_term = r.shift_months(-duration, -duration)

    statuses = current_tenancies.values("status").annotate(total=Count("id"))
    status_dict: dict[str, int] = {s["status"]: s["totals"] for s in statuses}

    current_tenancies_count = current_tenancies.count()
    previous_tenancies_count = tenancy_during(previous_term).count()

    totals = current_tenancies.aggregate(
        total_expected=Sum("total_due"),
    )
    return {
        **status_dict,
        "duration": duration,
        "actual_expected": totals["total_expected"] or Decimal(0),
        "uptake": (current_tenancies_count - previous_tenancies_count)/previous_tenancies_count
    }

def get_current_tenant_prefetch() -> Prefetch:
    r = DateRange.for_month(timezone.now().date())
    return Prefetch("tenancy_set", tenancy_during(r) , to_attr="_current_tenant")
