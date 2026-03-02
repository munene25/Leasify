from structlog import getLogger
from users.models import User, Account
from django.db import transaction

logger = getLogger("users.services.unsub")

@transaction.atomic
def account_unsubscribe(account: Account) -> Account:
    """
    Unsubscribes a user from the mailing list.
    """
    if account.can_receive_emails:
        account.can_receive_emails = False
        account.save()
    logger.info(f"user [user_id: {account.user_id}] unsubscribed from mailling list")  # type: ignore
    return account



@transaction.atomic
def user_deactivate(user: User) -> User | None:
    """
    Allows deletion or deactivation of account.
    Denies permission an actor(Administrator) deleting or deactivating a super_user or staff member
    """     
    user.is_active = False
    user.save()
    logger.info(f"user [user_id: {user.pk}] deactivated.")
    return user
    