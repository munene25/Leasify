from .models import User
from rest_framework.exceptions import NotFound
from django.db import models
from tenancy.models import Tenancy
from tenancy import selectors as tenancy_selectors

def user_list():
    return User.objects.all()

def user_get_by_id(user_id):
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise NotFound({"user_id": "user not found"})


def user_get_by_email(*, user_email):
    try:
        return User.objects.get(email=user_email)
    except User.DoesNotExist:
        raise NotFound({"user_email": "user not found"})