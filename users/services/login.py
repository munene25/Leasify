from structlog import getLogger
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

logger = getLogger("users.services.login")

def user_login(email: str, password: str) -> tuple[AbstractUser, dict]:
    user = authenticate(email=email, password=password)
    if user is None:
        err = "No credentials match the email and password you provided"
        logger.warning(f"Invalid password or email for [user_emai: {email}]")
        raise AuthenticationFailed({"email": [err], "password": [err]})

    if not user.is_active:
        err = "You are barred from logging in to your account. Please contact system admin for further assistance"
        logger.warning(f"user [user_email: {email}] login denied for inactive account ")
        raise AuthenticationFailed(err)

    user.last_login = timezone.now()
    user.save()

    # TODO: Move this logic into views
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    tokens = {"access": access, "refresh": refresh}

    logger.info(f"user [user_id: {user.pk} logged in")
    return user, tokens
