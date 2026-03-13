from typing import Any
from django.http import QueryDict
from django.contrib.auth.models import Group
from rest_framework.exceptions import NotFound
import django_filters
from users.models import User
from django.db import models

PRIVILEGED_USERS = (
    models.Q(is_superuser=True) |
    models.Q(is_staff=True) |
    models.Q(groups__name="manager")
)

def user_list(filters: dict[str, Any] | QueryDict | None = None):
    """
    Fetches the user list with filtering
    """

    class UserFilter(django_filters.FilterSet):
        search = django_filters.CharFilter(method="search_fields")

        class Meta:
            model = User
            fields = ("is_active",)

        def search_fields(self, queryset, name, value):
            qs = queryset.filter(
                models.Q(first_name__icontains=value)
                | models.Q(last_name__icontains=value)
                | models.Q(email__icontains=value)
                | models.Q(account__phone_number__contains=value)
            )
            return qs

    users = User.objects.select_related("account").exclude(PRIVILEGED_USERS)
    return UserFilter(filters, users).qs


def user_get_locked(user_id: int) -> User:
    try:
        return User.objects.select_related("account").select_for_update().get(pk=user_id)
    except User.DoesNotExist:
        raise NotFound({"user_email": "user not found"})


def user_get_by_id(user_id: int):
    try:
        return User.objects.select_related("account").get(pk=user_id)
    except User.DoesNotExist:
        raise NotFound({"user_id": "user not found"})



def user_get_safe(user_id: int) -> User:
    """
    Fetch based on user_id
    Omits priviledged users defined in PRIVILEDGED_USERS
    """
    user = User.objects.filter(pk=user_id).exclude(PRIVILEGED_USERS).first()
    if user is not None: return user
    else: raise NotFound({"user_id": "user not found"})


def user_get_by_email(user_email):
    try:
        return User.objects.get(email=user_email)
    except User.DoesNotExist:
        raise NotFound({"user_email": "user not found"})


def user_list_roles():
    return Group.objects.all()
