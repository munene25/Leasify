from typing import TypedDict
from typing_extensions import Unpack

from structlog import getLogger

from django.db import transaction
from django.utils import timezone

from leasify.common.exceptions import EmailUpdateError
from leasify.users.models import User, Account, EMAIL_COOLDOWN

logger = getLogger("users.services.update")


class UserUpdateData(TypedDict, total=False):
    """Represents the payload expected for the user_update function"""

    first_name: str
    last_name: str
    phone_number: str
    backup_email: str


@transaction.atomic
def user_update(user: User, **kwargs: Unpack[UserUpdateData]):
    """
    Updates user and account information in a single transaction.

    Updates first_name, last_name for the user and phone_number, backup_email
    for the account. Only fields that differ from their current values are updated.

    :param user: User obj
    :param kwargs: Dictionary containing user and account update fields

    :return: Updated user instance

    :raises EmailUpdateError: If email update is attempted during cooldown period
    """

    USER_FIELDS = {"first_name", "last_name"}
    ACCOUNT_FIELDS = {"phone_number", "backup_email"}

    user_updates, account_updates = [], []
    account = user.account

    if backup_email := kwargs.get("backup_email"):
        kwargs["backup_email"] = User.objects.normalize_email(backup_email)

    for field, value in kwargs.items():

        if field in USER_FIELDS and getattr(user, field, value) != value:
            setattr(user, field, value)
            user_updates.append(field)

        elif field in ACCOUNT_FIELDS and getattr(account, field, value) != value:
            setattr(account, field, value)
            account_updates.append(field)

    if user_updates:
        user.full_clean()
        user.save(update_fields=user_updates)

    if account_updates:
        account.full_clean()
        account.save(update_fields=account_updates)

    logger.info("user_updated", target_id=user.pk, fields=[*user_updates, *account_updates])

    return user


def account_update_mailing_status(account: Account, status: bool) -> Account:
    """
    Changes ability of a user to receive non-critical mail in their inbox.

    :param account: account obj
    :param status: Status to update to
    
    :return: unsubed account instance
    """
    account.can_receive_emails = status
    account.save(update_fields=["can_receive_emails"])
    logger.info("account_mailing_status_updated", target_id=account.user_id, status=status)
    return account


def user_update_active_status(user: User, status: bool) -> User:
    """
    Simplified the delete/deactivate dance: No deletions apart from through the admin.
    This service serves both the user and admin deactiavations

    :param user: The user obj
    :param status: Status to update to

    :return: deactivated user
    """
    user.is_active = status
    status_change = {True: "activated", False: "deactivated"}[status]
    user.save(update_fields=["is_active"])
    logger.info("users_active_status_updated", target_id=user.pk, status=status_change)
    return user


def user_email_update(user: User, email: str, password: str) -> User:
    """
    Email updater that limits email changes based on EMAIL_COOLDOWN in model.

    :param user: User obj
    :param email: the intended email to change to
    :param password: current password for the user

    :return: user
    """
    user.verify_password(password)

    # Ensure change is available
    if user.next_email_change is not None:
        raise EmailUpdateError({"email": f"Email updates are allowed once every {EMAIL_COOLDOWN.days} days"})

    # Normalize email first
    user.email = User.objects.normalize_email(email)

    user.verified = False
    user.last_email_change = timezone.now()

    user.full_clean()
    user.save(update_fields=["email", "verified", "last_email_change"])
    logger.info("user_email_updated", target_id=user.pk, email=user.email)
    return user
