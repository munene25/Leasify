from structlog import getLogger
from django.db import transaction
from django.contrib.auth.models import Group
from users.models import User, Account

logger = getLogger("users.services.deactiavate")


@transaction.atomic
def account_unsubscribe(account: Account) -> Account:
    """
    Unsubscribes a user from the mailing list.

    :param account: account obj
    :type account: Account

    :return: unsubed account instance
    :rtype: Account
    """
    account.can_receive_emails = False
    account.save(update_fields=["can_receive_emails"])
    logger.info(f"user [user_id: {account.user_id}] unsubscribed from mailling list")  # type: ignore
    return account


@transaction.atomic
def user_deactivate(user: User) -> User:
    """
    Simplified the delete/deactivate dance: No deletions apart from the admin.
    This service serves both the user and admin deactiavations

    :param user: The user obj
    :type user: User

    :return: deactivated user
    :rtype: User
    """
    user.is_active = False
    user.save(update_fields=["is_active"])
    logger.info(f"user [user_id: {user.pk}] deactivated.")
    return user


@transaction.atomic
def user_remove_role(user: User) -> User:
    """
    Responsible for removing a user from all groups.
    Since only one role can be assigned to a user at a time, only one group will be removed.

    :param user: The user from whom the role will be removed.
    :type user: User
    :return: The user with the role removed.
    :rtype: User
    """

    role = user.groups.first()
    user.groups.remove(role)
    logger.info(f"Roles [role: {role}] removed from [user_id: {user.pk}]")
    return user
