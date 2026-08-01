from leasify.users.models import User
from django.db.models import Q
from typing import Callable

class FilteringPolicy:
    """
    A tiered mapping of how each role affects how list views are rendered based on the user's role
    ! Important: UNAUTHENTICATED USERS ARE TREATED AS REGULAR USERS
    """

    SUPERUSER: Q | Callable[..., Q]
    MANAGER: Q | Callable[..., Q]
    CARETAKER: Q | Callable[..., Q]
    TENANT: Q | Callable[..., Q]
    REGULAR: Q | Callable[..., Q]

    @classmethod
    def for_user(cls, user: User) -> Q:
        role = getattr(user, "role", "regular")
        base_exclusion = {
            "superuser": cls.SUPERUSER,
            "manager": cls.MANAGER,
            "caretaker": cls.CARETAKER,
            "tenant": cls.TENANT,
            "regular": cls.REGULAR,
        }[role]
        
        if callable(base_exclusion):
            return base_exclusion(user)
        return base_exclusion

        