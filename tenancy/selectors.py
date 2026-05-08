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
    """
    Superuser, manager and caretaker should be able to view all tenancies.
    Other users should be able to view tenancies belonging to them.
    """

    SUPERUSER = MANAGER = CARETAKER = Q()
    TENANT = REGULAR = lambda user: Q(user_id=user.pk)


BASE_QS: QuerySet[Tenancy] = Tenancy.objects.select_related("user", "apartment", "semester")

tenancy_not_found = raise_not_found("tenancy_id", "Tenancy does not exist.")


def tenancy_list_for(user: "User", filters: QueryDict | dict[str, Any]) -> QuerySet[Tenancy]:
    """
    List tenancies based on who is requesting
    """
    import django_filters

    class TenancyFilter(django_filters.FilterSet):
        class Meta:
            model = Tenancy
            fields = ("total_paid",)

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


@tenancy_not_found
def tenancy_get(tenancy_id: int) -> Tenancy:
    """Get tenant outside of client flows"""

    return BASE_QS.get(pk=tenancy_id)


def tenancy_recent(user: "User") -> Tenancy | None:
    """
    This selector optimizes the check for getting the most recent tenancy for a user.
    It could also include the tenancy belonging in the grace period if occurs in the previous semester
    """
    from semesters.models import GRACE_PERIOD
    from django.utils import timezone

    now = timezone.now().date()
    extension = now - GRACE_PERIOD
    return (
        Tenancy.objects.select_related("semester")
        .order_by("-semester__start_date")
        .filter(user_id=user.pk, semester__start_date__lte=now, semester__end_date__gte=extension)
        .first()
    )


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


def tenancy_overview(semester: "Semester | None" = None):
    """
    This selector provides an overview of the tenancies for a given semester, including:
    - The number of tenants that are cleared and not cleared.
    - The most and least popular apartments based on the number of tenancies.
    - The total expected rent and total collected rent for the semester.
    """
    from django.db.models import Sum, F, Count, Value, DecimalField, Case, When
    from decimal import Decimal
    from semesters.selectors import semester_current

    s = semester or semester_current()
    previous_semester = Semester.objects.filter(end_date__lt=s.start_date).first()
    tenancies = BASE_QS.all()
    statuses = (
        tenancies.filter(semester_id=s.pk).annotate(
            status=Case(
                When(total_paid__lt=F("lease_rent"), then=Value("not_cleared")),
                default=Value("cleared"),
            )
        )
        # Group by status
        .values("status")
        # then annotate the count on the statuses
        .annotate(
            tenants=Count("id"),
        )
    ).all()
    totals = tenancies.aggregate(
        total_expected=Sum("lease_rent"),
        total_collected=Sum("total_paid"),
    )
    uptake = tenancies.filter(semester=s).count() - tenancies.filter(semester=previous_semester).count()
    return {
        "cleared": [s["tenants"] for s in statuses if s["status"] == "cleared"][0],
        "not_cleared": [s["tenants"] for s in statuses if s["status"] == "not_cleared"][0],
        "actual_expected": totals["total_expected"] or Decimal(0),
        "total_collected": totals["total_collected"] or Decimal(0),
        "uptake_from_previous_semester": uptake,
    }

current_tenant_prefetch = lambda: Prefetch("tenancy_set", tenancy_for_semester(), to_attr="_current_tenant")
