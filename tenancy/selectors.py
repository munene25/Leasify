from django.db.models import Prefetch, QuerySet
from .models import Tenancy
from rest_framework.exceptions import NotFound

prefetch_user_apt_sem = Prefetch(
    "tenancy_set",
    Tenancy.objects.all().select_related("user", "apartment", "semester"),
)
base_qs = Tenancy.objects.select_related("user")


def tenancy_list() -> QuerySet:
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
        return Tenancy.objects.select_related("apartment", "semester", "user").get(pk=tenancy_id)
    except Tenancy.DoesNotExist:
        raise NotFound({"tenancy_id": "Tenancy not found"})


def tenancy_current() -> QuerySet[Tenancy]:
    """
    Filter out the current tenant in that semester if the semester exists 
    It is important to decouple the semester existing or not in order to get the current tenant.
    """
    from semesters.selectors import semester_current
    
    # better to use the cached object through current semester selector
    try:
        sem = semester_current()
        return base_qs.filter(semester_id=sem.pk)
    except NotFound:
        return Tenancy.objects.none()
