from typing import Any
from functools import lru_cache
from django.db.models import Q
from django.http import QueryDict
from django.db.models.query import QuerySet
from django.contrib.auth.models import Group
from leasify.users.models import User
from leasify.common.helpers import raise_not_found
from leasify.common.domain import FilteringPolicy

# base queryset with related account to avoid repetition of select_related in each selector
BASE_QS = User.objects.select_related("account")

# Initialize the raise_not_found wrapper for most common exception
user_not_found = raise_not_found("user_id", "User with given id not found")


class UserFilterPolicy(FilteringPolicy):
    SUPERUSER = Q()
    MANAGER = Q(is_superuser=False)
    CARETAKER = Q(is_superuser=False) & ~Q(groups__name__in=["manager", "caretaker"])
    TENANT = lambda user: Q(pk=user.pk)
    REGULAR = lambda user: Q(pk=user.pk)


def user_list_for(*, user: User, filters: dict[str, Any] | QueryDict = {}) -> QuerySet:
    """
    Fetches the visible user list for the requesting user
    Allows filtering based on fileds "search" and "is_active"
    search includes: first_name, last_name, email and account__phone_number
    """
    import django_filters

    class F(django_filters.FilterSet):
        search = django_filters.CharFilter(method="search_fields")

        class Meta:
            model = User
            fields = ("is_active",)

        def search_fields(self, queryset, name, value):
            return queryset.filter(
                Q(first_name__icontains=value)
                | Q(last_name__icontains=value)
                | Q(email__icontains=value)
                | Q(account__phone_number__contains=value)
            )

    u_filters = UserFilterPolicy.for_user(user)
    users = BASE_QS.filter(u_filters).exclude(pk=user.pk)
    return F(filters, users).qs


@user_not_found
def user_get(user_id: int) -> User:
    """
    The primary way to fetch data for non admin routes and within domain in regular
    """
    return BASE_QS.get(pk=user_id)


@user_not_found
def user_get_for(*, user: User, user_id: int) -> User:
    """
    This is primarily for admin routes to exclude certain users from the queryset
    User will *only* be able to view users intended to be visible to them.
    """

    exclusions = UserFilterPolicy.for_user(user)
    return BASE_QS.filter(exclusions).get(pk=user_id)


@raise_not_found("email", "User with given email not found")
def user_get_by_email(user_email: str) -> User:
    """
    Used in views where the email is the only identifying attribute eg. password-reset
    Should first normalize the email then try to get the user
    """

    email = User.objects.normalize_email(user_email)
    return BASE_QS.get(email=email)


def groups_list() -> QuerySet[Group]:
    """
    Exists as a User selector as it's highly coupled with the user model
    """
    return Group.objects.all()


@lru_cache(maxsize=5)
@raise_not_found("group", "Group does not exist")
def get_group(name: str) -> Group:
    return Group.objects.get(name=name)
