from users.models import User
from django.db.models import Q


class RoleBasedExclusions:
    """
    A tiered mapping of how each role affects how list views are rendered based on the user's role
    """

    SUPERUSER: Q
    MANAGER: Q
    CARETAKER: Q
    TENANT: Q
    GENERAL: Q

    @classmethod
    def for_user(cls, user: User):
        base_exclusion = {
            "superuser": cls.SUPERUSER,
            "manager": cls.MANAGER,
            "caretaker": cls.CARETAKER,
            "tenant": cls.TENANT,
            "general": cls.GENERAL,
        }[user.role]
        return base_exclusion