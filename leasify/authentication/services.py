from structlog import getLogger

from django.contrib.auth import authenticate
from django.contrib.auth.models import AbstractUser, BaseUserManager
from rest_framework.exceptions import ValidationError, AuthenticationFailed, NotFound

from leasify.authentication import google
from leasify.users.models import User
from leasify.authentication import tasks

logger = getLogger("authentication.services")


def user_authenticate(*, email: str, password: str) -> AbstractUser:
    """
    Authenticates the user and updates their last login
    Incorrect credentials or inactive users raise Authentication Error

    :param email: email for the user
    :param password: user's password
    :return: returns a user or will raise an 401 if authentication failed
    """

    normalized_email = BaseUserManager.normalize_email(email)
    user = authenticate(email=normalized_email, password=password)
    if user is None:
        err = "Incorrect email or password"
        logger.warning("user_authentication_failed", email=email)
        raise AuthenticationFailed({"email": [err], "password": [err]})

    # user_login from django.contrib.auth.user_login will update last_login
    logger.info("user_authenticated", target_id=user.pk)
    return user


def user_change_password(*, user: User, new_password: str, url_path: str, password: str | None = None, is_ressetting: bool = False) -> User:
    """Password change for user via reset or with old password"""
    # ! Password changes automatically invalidate issued cookies
    # ! CRITICAL BUG Found
    # Calling check_password does not raise an error
    # To mitigate this an explicit flag guarantees the password is checked.
    # Also necessary to call **verify_password** not 'check_password'

    if not is_ressetting:
        if not password:
            raise ValidationError({"password": "Please provide a password"})
        else:
            user.verify_password(password)
    user.validate_password(new_password)
    user.set_password(new_password)
    user.full_clean()
    user.save(update_fields=["password"])
    status = {True: "user_password_reset", False: "user_password_changed"}[is_ressetting]
    logger.warning(status, target_id=user.pk)
    tasks.notify_password_change.delay(user.pk, url_path)
    return user


def user_email_verify(user: User) -> User:
    """
    Simply verifies the user in a transaction,
    Could add more features in the future like a confirmaiton email.

    :param user: User object
    :return: A user that is verified
    """
    user.verified = True
    user.save(update_fields=["verified"])
    logger.info("user_email_verified", target_id=user.pk)
    return user


def google_authenticate(token: str) -> User:
    from leasify.users.choices import AccountType

    claims = google.verify_claims(token)

    # Try by provider_id first (most reliable)
    try:
        return User.objects.get(account__provider_id=claims["provider_id"])
    except User.DoesNotExist:
        pass

    try:
        return User.objects.get(email=claims["email"])
    except User.DoesNotExist:
        pass
        
    # Create new user
    return User.objects.create_user(
        account_type=AccountType.GOOGLE,
        notify=False,
        **claims
    )