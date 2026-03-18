from django.contrib.auth.models import AbstractUser, AnonymousUser
from rest_framework.exceptions import PermissionDenied, NotAuthenticated


def check_perms(user: AnonymousUser | AbstractUser, permission: str):
    print("USER AUTHENTICATION" ,user.is_authenticated)
    if not user.is_authenticated:
        print("RAISING 401")
        raise NotAuthenticated()
    if not user.has_perm(permission):
        raise PermissionDenied("Only priviledged users are allowed to perform this action")
