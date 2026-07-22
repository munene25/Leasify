from typing import Any, TYPE_CHECKING
from django.http.request import QueryDict
from django.db.models import Q, QuerySet, Prefetch
from tenancy.models import Tenancy
from common.helpers import raise_not_found
from common.domain import FilteringPolicy
from tenancy.choices import *

if TYPE_CHECKING:
    from users.models import User

BASE_QS = Tenancy.objects.select_related("user", "apartment")

tenancy_not_found = raise_not_found("tenancy_id", "Tenancy does not exist.")


class TenancyFilterPolicy(FilteringPolicy):
    """
    Superuser, manager and caretaker should be able to view all tenancies.
    Other users should be able to view tenancies belonging to them.
    """

    SUPERUSER = Q()
    MANAGER = Q()
    CARETAKER = Q()
    TENANT = lambda user: Q(user_id=user.pk)
    REGULAR = lambda user: Q(user_id=user.pk)


def tenancy_list_for(*, user: "User", filters: QueryDict | dict[str, Any]) -> QuerySet[Tenancy]:
    """
    List tenancies based on who is requesting
    """
    import django_filters

    class TenancyFilter(django_filters.FilterSet):
        class Meta:
            model = Tenancy
            fields = ("status", "apartment")

        search = django_filters.CharFilter(method="search_fields")
        joined = django_filters.DateFromToRangeFilter(field_name="date_joined")

        def search_fields(self, queryset, name, value: str):
            q = Q()
            if value.isdigit():
                q |= Q(apartment__unit_number=value)
            else:
                q |= Q(apartment__block__icontains=value)
                q |= Q(user__first_name__icontains=value)
                q |= Q(user__last_name__icontains=value)
            return queryset.filter(q).distinct()

    t_filters = TenancyFilterPolicy.for_user(user)
    tenancies = BASE_QS.filter(t_filters)
    return TenancyFilter(filters, tenancies).qs


@tenancy_not_found
def tenancy_get_for(user: "User", tenancy_id: int) -> Tenancy:
    """Will filter out the tenancies viewable only to the user based on the policy"""

    t_filters = TenancyFilterPolicy.for_user(user)
    return BASE_QS.filter(t_filters).get(pk=tenancy_id)


def tenancy_in(states: list[TenancyStatus]) -> QuerySet[Tenancy]:
    """
    Quickly fetch tenancies in this the states
    :param states: statuses to filter
    :return: Tenancy QuerySet filtered by state
    """
    return Tenancy.objects.filter(status__in=states)


CURRENT_TENANT = Prefetch(
    "tenancy_set", tenancy_in(ACTIVE_RESERVED_OR_DEFAULTING).select_related("user"), to_attr="_active_tenant"
)
