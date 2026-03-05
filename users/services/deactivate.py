from structlog import getLogger
from users.models import User, Account
from django.db import transaction

logger = getLogger("users.services.unsub")

@transaction.atomic
def account_unsubscribe(account: Account) -> Account:
    """
    Unsubscribes a user from the mailing list.

    :param account: account obj
    :type accoutn: Account

    :return: unsubed account instance
    :rtype: Account
    """
    if account.can_receive_emails:
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
    if user.is_active:
        user.is_active = False
        user.save(update_fields=["is_active"])
        logger.info(f"user [user_id: {user.pk}] deactivated.")
    return user
    