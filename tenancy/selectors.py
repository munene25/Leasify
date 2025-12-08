from django.db.models import Prefetch, QuerySet
from .models import Tenancy
from rest_framework.exceptions import NotFound

prefetch_user_apt_sem = Prefetch(
    "tenancy_set",
    Tenancy.objects.all().select_related("user", "apartment", "semester"),
)

def tenancy_list()-> QuerySet:
    return Tenancy.objects.select_related("apartment", "user").all()

def tenancy_for_update(tenancy_id: int) -> Tenancy:
    """Fetches the tenancy and related apartment for update"""
    try:
        return Tenancy.objects.select_related("apartment", "user").select_for_update().get(pk=tenancy_id)
    except Tenancy.DoesNotExist:
        raise NotFound({"tenancy_id": "Tenancy not found"})

def tenancy_get_by_user_id(*, user_id: int):
    try:
        return Tenancy.objects.select_related("user").get(user_id=user_id)
    except Tenancy.DoesNotExist:
        raise NotFound({"tenancy_id": ["Tenancy not found"]})

def tenancy_get_by_apartment_id(apartment_id: int):
    return Tenancy.objects.select_related("apartment").filter(apartment=apartment_id)


def tenancy_get_by_id(tenancy_id: int):
    try:
        return Tenancy.objects.select_related("apartment", "semester", "user").get(
            pk=tenancy_id
        )
    except Tenancy.DoesNotExist:
        raise NotFound({"tenancy_id": "Tenancy not found"})

