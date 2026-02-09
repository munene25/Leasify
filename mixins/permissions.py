from django.contrib.auth.models import AbstractUser, AnonymousUser
from rest_framework.exceptions import PermissionDenied, AuthenticationFailed


class PermissionMixin:
    def check_perms(self, user: AnonymousUser|AbstractUser, permission: str):
        if not user.is_authenticated:
            raise PermissionDenied("Authentication is required")
        if not user.has_perm(permission):
            raise PermissionDenied("Only priviledged users are allowed to perform this action")

