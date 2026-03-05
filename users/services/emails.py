from structlog import getLogger
from users.models import User
from django.db import transaction
from rest_framework.exceptions import ValidationError
from django.utils import timezone

logger = getLogger("users.services.emails")


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
    if user.verified:
        return user
    user.verified = True
    user.save(update_fields=["email"])
    logger.info(f"user verified their email")
    return user


@transaction.atomic
def user_email_update(user: User, email: str, password: str) -> User:
    """
    Email updater that limits email changes to once per 2 weeks.

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
        err = f"Next available email change is '{user.next_email_change}'"
        raise ValidationError({"email": [err]})

    # Normalize email first
    user.email = User.objects.normalize_email(email)

    user.verified = False
    user.last_email_change = timezone.now()

    user.full_clean()
    user.save(update_fields=["email", "verified", "last_email_change"])
    logger.info(f"email address changed for user [{user}]")
    return user
