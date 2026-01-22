from .models import User
from rest_framework.exceptions import NotFound
from django.db import models
from tenancy.models import Tenancy
from tenancy import selectors as tenancy_selectors

def user_list():
    return User.objects.all()

def users_get_visible_for(user: User):
    if user.is_superuser or user.is_staff:
        return User.objects.select_related("account").all()
    return user

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