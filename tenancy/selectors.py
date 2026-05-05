from typing import Any, TYPE_CHECKING
from django.http.request import QueryDict
from django.db.models import Q, F, QuerySet, Prefetch
from tenancy.models import Tenancy
from common.helpers import raise_not_found
from common.domain import FilteringPolicy

if TYPE_CHECKING:
    from semesters.models import Semester
    from users.models import User


class TenancyFilterPolicy(FilteringPolicy):
    SUPERUSER =  MANAGER = CARETAKER = Q()
    TENANT = REGULAR = lambda user: Q(user_id=user.pk)


BASE_QS = Tenancy.objects.select_related("user", "apartment")

tenancy_not_found = raise_not_found("tenancy_id", "Tenancy does not exist.")


def tenancy_list_for(user: "User", filters: QueryDict | dict[str, Any]) -> QuerySet[Tenancy]:
    
    
    import django_filters

    class TenancyFilter(django_filters.FilterSet):
        class Meta:
            model = Tenancy
            fields = ("total_paid", )

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
            from semesters.models import Semester

            # Need to filter based on year, start_month or end_month:
            start_date, end_date = Semester.get_date_range(value)

            return queryset.filter(semester__end_date__gte=start_date, semester__start_date__lte=end_date)  

    t_filters = TenancyFilterPolicy.for_user(user)
    tenancies = BASE_QS.select_related("semester").filter(t_filters)
    return TenancyFilter(filters, tenancies).qs

@tenancy_not_found
def tenancy_lock(tenancy_id: int) -> Tenancy:
    """
    Fetches the tenancy and related apartment for update.
    Important: It selects the apartment for update as well for payment computations.
    """

    return Tenancy.objects.select_related("apartment").select_for_update().get(pk=tenancy_id)

@tenancy_not_found
def tenancy_get_for(user: "User", tenancy_id: int) -> Tenancy:
    """Will filter out the tenancies viewable only to the user based on the policy"""

    t_filters = TenancyFilterPolicy.for_user(user)
    return BASE_QS.filter(t_filters).get(pk=tenancy_id)


def tenancy_for_semester(semester: "Semester | None" = None) -> QuerySet[Tenancy]:
    """
    Defaults to current_semester.
    Filter out the tenants in that semester.
    If semester does not exists, it will default no tenant
    It is important to decouple the semester existing or not in order to get the current tenant.
    """
    from semesters.selectors import semester_current
    from rest_framework.exceptions import NotFound

    try:
        # better to use the cached object through current_semester selector
        sem = semester or semester_current()
        return Tenancy.objects.select_related("user").filter(semester_id=sem.pk)
    except NotFound:
        # This is in cases where the semester is none
        return Tenancy.objects.none()

current_tenant_prefetch = lambda: Prefetch("tenancy_set", tenancy_for_semester(), to_attr="_current_tenant")