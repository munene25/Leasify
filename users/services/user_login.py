from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

def user_login(email: str, password: str) -> tuple[AbstractUser, dict]:
    user = authenticate(email=email, password=password)
    if user is None:
         if user is None:
            err = "No credentials match the email and password you provided"
            raise AuthenticationFailed({"email": [err], "password": [err]})

    if not user.is_active:
        err = "You cannot log in to your account. Please contact admin for further assistance"
        raise AuthenticationFailed(err)

    user.last_login = timezone.now()
    user.save()

    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    tokens = {"access": access, "refresh": refresh}

    # TODO: send Email for login 
    return user, tokens
