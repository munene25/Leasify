from typing import TypedDict
from typing_extensions import Unpack
from structlog import getLogger
from users.models import User, Account, EMAIL_COOLDOWN
from django.db import transaction
from rest_framework.exceptions import ValidationError
from users.tasks import notify_password_change
from django.utils import timezone
from common.exceptions import EmailUpdateError

logger = getLogger("users.services.update")


class UserUpdateData(TypedDict, total=False):
    """Represents the payload expected for the user_update function"""

    first_name: str
    last_name: str
    phone_number: str
    bio: str
    backup_email: str


@transaction.atomic
def user_update(user: User, **kwargs: Unpack[UserUpdateData]):
    """
    User and Account model updates under a singular interface.

    :param user: User to be used as the related field
    :type user: User
    :param kwargs:
        first_name: str,
        last_name: str,
        phone_number: str,
        bio: str,
        backup_email: str
    :type kwargs: dict

    :return: Modified User object
    :rtype: User
    """
    USER_FIELDS = {"first_name", "last_name"}
    ACCOUNT_FIELDS = {"phone_number", "bio", "backup_email"}

    user_updates, account_updates = [], []
    account = user.account

    # Normalize email
    try:
        kwargs["backup_email"] = User.objects.normalize_email(kwargs["backup_email"]) # type: ignore
    except KeyError:
        pass

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
        logger.info("user_updated", target_id=user.pk, fields=user_updates)

    if account_updates:
        account.full_clean()
        account.save(update_fields=account_updates)
        logger.info("account_updated", target_id=user.pk, fields=account_updates)

    return user


@transaction.atomic
def user_change_password(*, user: User, new_password: str, password: str | None = None, is_ressetting: bool = False) -> User:
    """
    This service is used in both password recovery and password changes
    Therefore in password recovery flows, the current password is unknown
    Raw password is also required to check password validity


    :param user: User model instance
    :type user: User
    :param new_password: The password to be set if operation is successful
    :type new_password: str
    :param password: The current raw password of the user. Can be none in password recovery flows
    :type password: str | None

    :return: Modified User object
    :rtype: User
    """
    # ! Password changes automatically invalidate issued cookies
    # ! CRITICAL BUG Found
    # Calling check_password does not raise an error
    # To mitigate this an explicit flag guarantees the password is checked.
    # Also necessary to call **validate_password** not 'check_password'

    if not is_ressetting:
        if not password:
            raise ValidationError({"password": "Please provide a password"})
        else:
            user.validate_password(password)

    user.set_password(new_password)
    user.full_clean()
    user.save(update_fields=["password"])
    status = {True: "user_password_reset", False: "user_password_changed"}[is_ressetting]
    logger.warning(status, target_id=user.pk)
    transaction.on_commit(lambda: notify_password_change.delay(user.pk))
    return user


@transaction.atomic
def account_update_mailing_status(account: Account, status: bool) -> Account:
    """
    Changes ability of a user to receive non-critical mail in their inbox.

    :param account: account obj
    :type account: Account

    :return: unsubed account instance
    :rtype: Account
    """
    account.can_receive_emails = status
    account.save(update_fields=["can_receive_emails"])
    logger.info("account_mailing_status_updated", target_id=account.user_id, status=status)
    return account


@transaction.atomic
def user_update_active_status(user: User, status: bool) -> User:
    """
    Simplified the delete/deactivate dance: No deletions apart from through the admin.
    This service serves both the user and admin deactiavations

    :param user: The user obj
    :type user: User

    :return: deactivated user
    :rtype: User
    """
    user.is_active = status
    status_change = {True: "activated", False: "deactivated"}[status]
    user.save(update_fields=["is_active"])
    logger.info("users_active_status_updated", target_id=user.pk, status=status)
    return user

@transaction.atomic
def user_email_verify(user: User) -> User:
    """
    Simply verifies the user in a transaction,
    Could add more features in the future like a confirmaiton email.

    :param user: User object
    :type user: User

    :return: A user that is verified
    :rtype: User
    """
    user.verified = True
    user.save(update_fields=["verified"])
    logger.info("user_email_verified", target_id=user.pk)
    return user


@transaction.atomic
def user_email_update(user: User, email: str, password: str) -> User:
    """
    Email updater that limits email changes based on EMAIL_COOLDOWN in model.

    :param user: User obj
    :type user: User
    :param email: the intended email to change to
    :type email: str
    :param password: current password for the user
    :type password: str

    :return: user
    :rtype: User
    """
    user.validate_password(password)

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
