from typing import Any, TYPE_CHECKING
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

occupied = [Tenancy.Status.ACTIVE, Tenancy.Status.PENDING]

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
            from common.period import PartialRange
            
            try:
                r = PartialRange.from_string(value)
            except (ValueError, KeyError):
                raise ValidationError("Cannot parse date ranges. Format is 'period=start=YYYY-MMM,end=YYYY-MMM'")

            return queryset.filter(end_date__gte=r.start, start_date__lte=r.end)

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



def current_tenant() -> Prefetch:
    return Prefetch("tenancy_set", Tenancy.objects.filter(status__in=[Tenancy.Status.ACTIVE]) , to_attr="_active_tenants")
