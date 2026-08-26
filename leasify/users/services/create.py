from typing import Any
from structlog import getLogger

from django.db import transaction

from leasify.users import tasks
from leasify.users.services import providers, utils
from leasify.users.models import User, Account
from leasify.users.choices import AccountType

logger = getLogger("users.services.create")


@transaction.atomic
def user_create(email: str, first_name: str, last_name: str, account_type: AccountType, notify: bool, **kwargs: Any) -> User:
    """
    Create a new user and account based on the provided account type.

    :param email: The email address of the new user. Must be a valid email format.
    :param first_name: The first name of the new user.
    :param last_name: The last name of the new user.
    :param account_type: The type of account to create (e.g., 'customer', 'staff', 'superuser').
    :param notify: If True, sends a welcome email with unsubscribe and email verification URLs.
    :param kwargs: Additional keyword arguments passed for account creation.
        - is_staff: Whether the user is a staff member (bool)
        - is_active: Whether the user is active (bool)
        - is_superuser: Whether the user is a superuser (bool)
        - backup_email: An optional backup email address (str)
        - phone_number: An optional phone number (str)
        - unsubscribe_url: URL for unsubscribing from emails (str)
        - email_verify_url: URL for email verification (str)
    
    :return: The created User object.
    :raises: Various exceptions depending on the account type handler.
    """

    email = User.objects.normalize_email(email)

    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_staff=kwargs.get("is_staff"),
        is_active=kwargs.get("is_active"),
        is_superuser=kwargs.get("is_superuser"),
    )

    backup_email = User.objects.normalize_email(kwargs.get("backup_email"))
    account = Account(
        user=user, 
        type=account_type, 
        phone_number=kwargs.get("phone_number"), 
        backup_email=backup_email,
    )

    providers.HANDLERS[account_type](user=user, account=account, kwargs=kwargs)
    user.full_clean()
    user.save()

    account.user = user
    account.full_clean()
    account.save()

    if notify:
        utils.require(kwargs, "unsubscribe_url", "email_verify_url")
        transaction.on_commit(
            lambda: tasks.send_welcome_email.delay(
                user.pk,
                unsubscribe_url=kwargs["unsubscribe_url"],
                email_verify_url=kwargs["email_verify_url"],
            )
        )
    logger.info("user_created", email=email, account_type=account_type, name=user.full_name)
    return user
