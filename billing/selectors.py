from django.db.models import Q, QuerySet
from typing import TYPE_CHECKING, Any
from django.http import QueryDict
from common.helpers import raise_not_found
from common.period import today
from common.domain import FilteringPolicy
from billing.models import BillingPeriod as BP
from billing.choices import BillingStatus as BS
import django_filters


if TYPE_CHECKING:
    from users.models import User
    from tenancy.models import Tenancy


billing_not_found = raise_not_found("billing_id", "Billing Period not found")
BASE_QS = BP.objects.select_related("tenancy__user").all()

class BillingFilteringPolicy(FilteringPolicy):
    SUPERUSER = Q()
    MANAGER = Q()
    CARETAKER = Q()
    TENANT = lambda u: Q(tenancy_id__in=list(u.tenancy_set.values_list('pk', flat=True)))
    REGULAR = Q(pk=0)


def billing_list_for(*, user: "User", filters: dict[str, Any] | QueryDict = {}) -> QuerySet[BP]:
    
    class F(django_filters.FilterSet): 
        class Meta:
            model = BP
            fields = ("status", )
        
        search = django_filters.CharFilter(method="search_fields")
        is_current = django_filters.BooleanFilter(method="filter_current")
        period = django_filters.DateFromToRangeFilter(field_name="start_date")
        status = django_filters.CharFilter(field_name="status")

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


      
    u_filters = BillingFilteringPolicy.for_user(user)
    qs = BASE_QS.filter(u_filters)
    return F(filters, qs).qs


@billing_not_found
def billing_get_for(user: "User", tenancy_id: int):
    u_filters = BillingFilteringPolicy.for_user(user)
    return BASE_QS.filter(u_filters).get(tenancy_id=tenancy_id)


@raise_not_found("billing", "No paid billing exists for the tenant")
def billing_last_paid_for(tenancy_id: int) -> BP:
    return BP.objects.filter(tenancy_id=tenancy_id, status=BS.PAID).latest("start_date")
