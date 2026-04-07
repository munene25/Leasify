from django.contrib.auth.models import AbstractUser, AnonymousUser
from rest_framework.exceptions import PermissionDenied, NotAuthenticated


class IsManager:
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name="manager").exists()


def check_perms(user: AnonymousUser | AbstractUser, permission: str) -> None:
    if not user.is_authenticated:
        raise NotAuthenticated()
    if not user.has_perm(permission):
        raise PermissionDenied("Only priviledged users are allowed to perform this action")

