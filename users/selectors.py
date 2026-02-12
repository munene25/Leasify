from .models import User
from rest_framework.exceptions import NotFound
import django_filters


def user_list(filters: dict|None = None):
    class UserFilter(django_filters.FilterSet):
        first_name = django_filters.CharFilter(lookup_expr="icontains")
        last_name = django_filters.CharFilter(lookup_expr="icontains")
        email = django_filters.CharFilter(lookup_expr="icontains")
        phone_number = django_filters.NumberFilter(field_name="account__phone_number", lookup_expr="icontains")
        class Meta:
            model = User
            fields = ['id']

            
    users = User.objects.select_related("account").all()
    filters = filters or {}
    return UserFilter(filters, users).qs

def user_get_locked(user_id: int):
    try:
        return User.objects.select_related("account").select_for_update().get(pk=user_id)
    except User.DoesNotExist:
        raise NotFound({"user_email": "user not found"})

def user_get_by_id(user_id: int):
    try:
        return User.objects.select_related("account").get(pk=user_id)
    except User.DoesNotExist:
        raise NotFound({"user_id": "user not found"})

def user_get_by_email(user_email):
    try:
        return User.objects.get(email=user_email)
    except User.DoesNotExist:
        raise NotFound({"user_email": "user not found"})