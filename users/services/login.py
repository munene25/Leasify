from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
import logging

logger = logging.getLogger("users.services.login")

def user_login(email: str, password: str) -> tuple[AbstractUser, dict]:
    user = authenticate(email=email, password=password)
    if user is None:
        err = "No credentials match the email and password you provided"
        logger.warning(f"Invalid password for {email}", extra={"actor": "anon"})
        raise AuthenticationFailed({"email": [err], "password": [err]})

    if not user.is_active:
        err = "You cannot log in to your account. Please contact admin for further assistance"
        logger.warning(f"User {email} deactivated for ", extra={"actor": "anon"})
        raise AuthenticationFailed(err)

    user.last_login = timezone.now()
    user.save()

    # TODO: Move this logic into views
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    tokens = {"access": access, "refresh": refresh}

    # TODO: send Email for login
    logger.info(f"User {email} Successful", extra={"actor": f"email: {email}"})
    return user, tokens
