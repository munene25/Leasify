from structlog import get_logger

from django.contrib.auth.models import Group

from leasify.users.models import User
from leasify.common.exceptions import RoleAssignmentError

logger = get_logger("users.services.roles")


def user_set_role(*, user: User, role: Group, replace: bool = False) -> User:
    """
    Assign a group role to a user.
    Replace forces overwriting user role

    :param user: The user to assign the role to.
    :param role: The group representing the role to assign.
    :param replace: Whether to replace any existing roles on the user.

    :return: The user with the assigned role.
    :raises RoleAssignmentError: If the user has another role and ``replace`` is False.
    """

    groups = list(user.groups.values_list("pk", flat=True))
    if role.pk in groups:
        logger.debug("user_role_already_exists", target_id=user.pk, role=role.name)
        return user

    if not replace and groups:
        raise RoleAssignmentError()

    user.groups.set([role])
    logger.info("user_role_updated", target_id=user.pk, role=role.name)
    return user


def user_remove_role(user: User) -> User:
    """
    Remove all group roles assigned to a user.

    :param user: The user whose roles should be removed.
    :return: The user without any assigned roles.
    """

    user.groups.clear()
    logger.warning("user_role_revoked", target_id=user.pk)
    return user
