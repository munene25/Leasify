from .models import Tenancy
from rest_framework.exceptions import NotFound
from django.db.models import Prefetch

prefetch_user_apt_sem = Prefetch(
    "tenancy_set",
    Tenancy.objects.all().select_related("user", "apartment", "semester"),
)


def tenancy_get_by_user_id(*, user_id: int):
    qs = Tenancy.objects.select_related("user").filter(user_id=user_id).first()


def tenancy_get_by_apartment_id(*, apartment_id: int):
    return Tenancy.objects.select_related("apartment").filter(apartment=apartment_id)


def tenancy_get_by_id(*, tenancy_id: int):
    try:
        return Tenancy.objects.select_related("apartment", "semester", "user").get(
            pk=tenancy_id
        )
    except Tenancy.DoesNotExist:
        raise NotFound({"tenancy_id": "tenancy not found"})

