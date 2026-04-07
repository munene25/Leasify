from typing import Any
import django_filters
from django.db.models import Q
from django.http import QueryDict
from django.contrib.auth.models import UserManager
from django.db.models.query import QuerySet
from django.contrib.auth.models import Group
from rest_framework.exceptions import NotFound
from users.models import User
from common.helpers import not_found


class UserRoleBasedExclusion:
    """
    A tiered mapping of how each role affects which users can be viewed by the role
    ! It also excludes the current user from the queryset
    """

    SUPERUSER = Q()
    MANAGER = Q(is_superuser=True)
    CARETAKER = MANAGER | Q(groups__name="manager")
    GENERAL = CARETAKER | Q(groups__name="caretaker")

    @classmethod
    def for_user(cls, user: User):
        base_exclusion = {
            "superuser": cls.SUPERUSER,
            "manager": cls.MANAGER,
            "caretaker": cls.CARETAKER,
            "general": cls.GENERAL,
        }[user.role]

        return base_exclusion | Q(pk=user.pk)


BASE_QS = User.objects.select_related("account")

# Initialize the not_found wrapper for most common exception
raise_not_found = not_found("user_id", "User with given id not found")


def user_list_for(*, user: User, filters: dict[str, Any] | QueryDict | None = None) -> QuerySet:
    """
    Fetches the visible user list for the requesting user
    Allows filtering based on fileds "search" and "is_active"
    search includes: first_name, last_name, email and account__phone_number
    """

    class UserFilter(django_filters.FilterSet):
        search = django_filters.CharFilter(method="search_fields")

        class Meta:
            model = User
            fields = ("is_active",)

        def search_fields(self, queryset, name, value):
            qs = queryset.filter(
                Q(first_name__icontains=value)
                | Q(last_name__icontains=value)
                | Q(email__icontains=value)
                | Q(account__phone_number__contains=value)
            )
            return qs

    exclusions = UserRoleBasedExclusion.for_user(user)
    users = BASE_QS.exclude(exclusions)
    return UserFilter(filters, users).qs


def user_list():
    """
    Get a full list of all the users in the db.
    """
    return BASE_QS.all()


@raise_not_found
def user_get(user_id: int) -> User:
    """
    The primary way to fetch data for non admin routes and within domain in general
    """
    return BASE_QS.get(pk=user_id)


def user_get_for(*, user: User, user_id: int) -> User:
    """
    This is primarily for admin routes to exclude certain users from the queryset
    User will *only* be able to view users intended to be visible to them.
    """

    exclusions = UserRoleBasedExclusion.for_user(user)
    matched_user = BASE_QS.filter(pk=user_id).exclude(exclusions).first()
    if matched_user is None:
        raise NotFound({"user_id": "user not found"})
    return matched_user


@not_found("email", "User with given email not found")
def user_get_by_email(user_email) -> User:
    """
    Used in views where the email is the only identifying attribute eg. password-reset
    Should first normalize the email then try to get the user
    """

    email = UserManager.normalize_email(user_email)
    return BASE_QS.get(email=email)


@raise_not_found
def user_get_locked(user_id: int) -> User:
    """
    Necessary for locking row access while updating
    """

    return BASE_QS.select_for_update().get(pk=user_id)


def groups_list():
    """
    Just decided to have this here because it is highly coupled with the user model
    """

    return Group.objects.all()
