from typing import Any

from django.db.models import Q
from django.http import QueryDict
from django.contrib.auth.models import UserManager
from django.db.models.query import QuerySet
from django.contrib.auth.models import Group
from users.models import User
from common.helpers import raise_not_found
from common.domain import RoleBasedExclusions

# base queryset with related account to avoid repetition of select_related in each selector
BASE_QS = User.objects.select_related("account")

# Initialize the raise_not_found wrapper for most common exception
user_not_found = raise_not_found("user_id", "User with given id not found")


class UserExclusions(RoleBasedExclusions):
    SUPERUSER = Q()
    MANAGER = Q(is_superuser=True)
    CARETAKER = MANAGER | Q(groups__name="manager")
    TENANT = CARETAKER | Q(groups__name="caretaker")
    GENERAL = TENANT


def user_list_for(*, user: User, filters: dict[str, Any] | QueryDict | None = None) -> QuerySet:
    """
    Fetches the visible user list for the requesting user
    Allows filtering based on fileds "search" and "is_active"
    search includes: first_name, last_name, email and account__phone_number
    """
    import django_filters

    class UserFilter(django_filters.FilterSet):
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

    exclusions = UserExclusions.for_user(user)
    users = BASE_QS.exclude(exclusions).exclude(pk=user.pk)
    return UserFilter(filters, users).qs

@user_not_found
def user_get(user_id: int) -> User:
    """
    The primary way to fetch data for non admin routes and within domain in general
    """
    return BASE_QS.get(pk=user_id)


@user_not_found
def user_get_for(*, user: User, user_id: int) -> User:
    """
    This is primarily for admin routes to exclude certain users from the queryset
    User will *only* be able to view users intended to be visible to them.
    """

    exclusions = UserExclusions.for_user(user)
    return BASE_QS.exclude(exclusions).get(pk=user_id)


@raise_not_found("email", "User with given email not found")
def user_get_by_email(user_email) -> User:
    """
    Used in views where the email is the only identifying attribute eg. password-reset
    Should first normalize the email then try to get the user
    """

    email = UserManager.normalize_email(user_email)
    return BASE_QS.get(email=email)


@user_not_found
def user_get_locked(user_id: int) -> User:
    """
    Necessary for locking row access while updating
    """

    return BASE_QS.select_for_update().get(pk=user_id)


def groups_list():
    """
    Exists as a User selector as it's highly coupled with the user model
    """
    return Group.objects.all()
