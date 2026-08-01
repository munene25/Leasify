from structlog import get_logger

from django.contrib.auth.models import Group

from leasify.users.models import User
from leasify.common.exceptions import RoleAssignmentError

logger = get_logger("users.services.roles")


def user_set_role(*, user: User, role: Group, replace: bool = False) -> User:
    """
    Responsible for adding a user to a group.
    Ensures that only one role can be assigned to a user at a time.
    replace flag explicitly requires the caller to acknowledge that an existing role will be replaced if it exists.

    :param user: The user to whom the role will be added.
    :type user: User

    :param role: The role (Group) to be added to the user.
    :type role: Group

    :param replace: If True, allows replacing an existing role.
    :type replace: bool

    :raises RoleAssignmentError: If the user already has a role and replace is False.
    
    :return: The user with the newly added role.
    :rtype: User
    """
    groups = list(user.groups.values_list('pk', flat=True))
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
    Responsible for removing a user from all groups.
    Since only one role can be assigned to a user at a time, only one group will be removed.

    :param user: The user from whom the role will be removed.
    :type user: User
    :return: The user with the role removed.
    :rtype: User
    """

    user.groups.clear()
    logger.warning("user_role_revoked", target_id=user.pk)
    return user
