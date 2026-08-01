from django.db.models import Q, QuerySet
from typing import TYPE_CHECKING, Any
from django.http import QueryDict
from leasify.common.helpers import raise_not_found
from leasify.common.period import today
from leasify.common.domain import FilteringPolicy
from leasify.billing.models import BillingPeriod as BP
from leasify.billing.choices import BillingStatus as BS
import django_filters


if TYPE_CHECKING:
    from leasify.users.models import User
    from leasify.tenancy.models import Tenancy


BASE_QS = BP.objects.select_related("tenancy__user").all()

class BillingFilteringPolicy(FilteringPolicy):
    SUPERUSER = Q()
    MANAGER = Q()
    CARETAKER = Q()
    TENANT = lambda u: Q(tenancy__user=u)
    REGULAR = Q(pk=0)


def billing_list_for(*, user: "User", filters: dict[str, Any] | QueryDict = {}) -> QuerySet[BP]:
    
    class F(django_filters.FilterSet): 
        class Meta:
            model = BP
            fields = ("status", )
        
        search = django_filters.CharFilter(method="search_fields")
        is_current = django_filters.BooleanFilter(method="filter_current")
        period = django_filters.DateFromToRangeFilter(method="filter_period")

        def search_fields(self, queryset, name, value):
            if not value.strip():
                return queryset
            qs = queryset.filter(
                Q(status__icontains=value)
                | Q(tenancy__user__first_name__icontains=value)
                | Q(tenancy__user__last_name__icontains=value)
            )
            return qs.distinct()

        def filter_current(self, queryset, name, value):
            now = today()
            return queryset.filter(start_date__lte=now, end_date__gte=now) if value else queryset

        def filter_period(self, queryset, name, value):
            if value.start:
                queryset = queryset.filter(end_date__gte=value.start)
            if value.stop:
                queryset = queryset.filter(start_date__lte=value.stop)
            return queryset
      
    u_filters = BillingFilteringPolicy.for_user(user)
    qs = BASE_QS.filter(u_filters)
    return F(filters, qs).qs


@raise_not_found("billing_id", "Billing not found")
def billing_get_for(*, user: "User", billing_id: int):
    u_filters = BillingFilteringPolicy.for_user(user)
    return BASE_QS.filter(u_filters).get(pk=billing_id)


@raise_not_found("billing", "No paid billing exists for the tenant")
def billing_last_paid(tenancy_id: int) -> BP:
    """Required because it raises a not found if no paid billing exists"""
    return BP.objects.filter(tenancy_id=tenancy_id, status=BS.PAID).latest("start_date")
