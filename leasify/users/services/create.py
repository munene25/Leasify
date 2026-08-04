from structlog import getLogger

from django.db import transaction

from rest_framework.exceptions import ValidationError

from leasify.users.models import User, Account
from leasify.users.tasks import send_welcome_email

logger = getLogger("users.services.create")


@transaction.atomic
def user_account_create(notify: bool=True, **kwargs) -> User:
    """Create user and account and send notification if notification is True"""

    user = user_create(email=kwargs["email"], password=kwargs["password"], first_name=kwargs["first_name"], last_name=kwargs["last_name"])
    account_create(user=user, phone_number=kwargs.get("phone_number"))

    if notify == True:
        errors = {}
        if not (unsub := kwargs.get("unsubscribe_url")):
            errors["unsubscribe_url"] = ["Please provide url path for user unsubscribe"]

        if not (verify := kwargs.get("email_verify_url")):
            errors["verify_url"] = ["Please provide url path for user verification"]

        if errors:
            raise ValidationError(errors)
        transaction.on_commit(lambda: send_welcome_email.delay(user.pk, unsub, verify))
    logger.info("user_account_created", target_id=user.pk, email=user.email)
    return user



def user_create(*, email: str, first_name: str, last_name: str, password: str) -> User:
    """
    Create a User Object. 
    
    :param email: The user's email
    :param first_name: The user's first name
    :param last_name: The user's last name
    :param password: The user's password

    :return: The created user instance
    """

    email = User.objects.normalize_email(email)
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        verified=False,
    )
    user.validate_password(password)
    user.set_password(password)
    user.full_clean()
    user.save()
    return user


def account_create(*, user: User, phone_number: str | None = None, bio: str | None = None, backup_email: str | None = None) -> Account:
    """
    Creates an account instance linked to a user one-one-field
    Phone number can be added later on and is not required.

    :param user: User to be used as the related field
    :type user: User
    :param phone_number: Phone number (region KE) for payment processing
    :type phone_number: str
    :param bio: About the user
    :type bio: str | None
    :param backup_email: Optional Backup email for account recovery
    :type backup_email: str | None
    :return: An account object
    :rtype: Account
    """

    if backup_email:
        backup_email = User.objects.normalize_email(backup_email)
    account = Account(user=user, bio=bio, backup_email=backup_email, phone_number=phone_number)
    account.full_clean()
    account.save()
    return account


