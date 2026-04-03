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


class PerRoleExclusion:
    """
    A tiered mapping of how each role affects which users can be viewed by the group/role
    ! It also excludes the current user from the queryset
    """
    SUPERUSER = Q()
    HIGH = Q(is_superuser=True)
    MODERATE = HIGH | Q(groups__name="manager")
    LOW = MODERATE | Q(groups__name="caretaker")

    @classmethod
    def for_user(cls, user: User):
        if user.is_superuser:
            base = cls.SUPERUSER
        elif "manager" in user.roles:
            base = cls.HIGH
        elif "caretaker" in user.roles:
            base = cls.MODERATE
        else:
            base = cls.LOW

        return base | Q(pk=user.pk)


BASE_QS = User.objects.select_related("account")

# Initialize the not_found wrapper for most common exception
raise_not_found = not_found("user_id", "User with given id not found")

def user_list_for(*, user: User, filters: dict[str, Any] | QueryDict | None = None) -> QuerySet:
    """
    Fetches the visible user list for the requesting user
    Allows filtering for fiels search and is_active
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

    exclusions = PerRoleExclusion.for_user(user)
    users = BASE_QS.exclude(exclusions)
    return UserFilter(filters, users).qs

def user_list():
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
        User will *only* be able to view users visible to them.
    """

    exclusions = PerRoleExclusion.for_user(user)
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
