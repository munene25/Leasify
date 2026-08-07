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
    """Create user and account based on the account types."""

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
