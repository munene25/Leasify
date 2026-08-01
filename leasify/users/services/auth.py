from structlog import getLogger
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import authenticate

logger = getLogger("users.services.authenticate")

def user_authenticate(*, email: str, password: str) -> AbstractUser:
    """
    Authenticates the user and updates their last login
    Incorrect credentials or inactive users raise Authentication Error

    :param email: email for the user
    :type email: str
    :param password: user's password
    :type password: str

    :return: returns a user or will raise an 401 if authentication failed 
    :rtype: User
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
