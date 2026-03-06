from structlog import getLogger
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import authenticate

logger = getLogger("users.services.login")

def user_login(*, email: str, password: str) -> AbstractUser:
    """
    Authenticates the user and updates their last login
    Incorrect credentials or inactive users raise Authentication Error

    :param email: email for the user
    :type email: str
    :param password: user's password
    :type password: str

    :return: returns a user or will raise an error if authentication failed 
    :rtype: User
    """
    normalized_email = BaseUserManager.normalize_email(email)
    user = authenticate(email=normalized_email, password=password)
    if user is None:
        err = "No credentials match the email and password you provided"
        logger.warning(f"Invalid password or email for [user_emai: {email}]")
        raise AuthenticationFailed({"email": [err], "password": [err]})

    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    logger.info(f"user [user_id: {user.pk} authenticated")
    return user
