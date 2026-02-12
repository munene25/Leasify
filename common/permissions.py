from django.contrib.auth.models import AbstractUser, AnonymousUser
from rest_framework.exceptions import PermissionDenied, AuthenticationFailed


def check_perms(user: AnonymousUser | AbstractUser, permission: str):
    if not user.is_authenticated:
        raise AuthenticationFailed("Authentication is required")
    if not user.has_perm(permission):
        raise PermissionDenied(
            "Only priviledged users are allowed to perform this action"
        )
