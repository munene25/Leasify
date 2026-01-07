from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from ..mixins import UserCookiesMixin


class UserLoginService:
    def __init__(self, **kwargs) -> None:
        self.email = kwargs.get("email")
        self.password = kwargs.get("password")

    def _check_empty_fields(self):
        # Serializers wiil gurantee the shape of the data
        # Included just as a sanity check
        err = "This field cannot be empty"
        if not self.email:
            raise ValidationError({"email": [err]})
        if not self.password:
            raise ValidationError({"password": [err]})

    def login(self):
        self._check_empty_fields()
        # Authenticate with email and password
        user = authenticate(
            email=self.email,
            password=self.password,
        )
        # Raise Authentication Error if no user found
        if user is None:
            err = "No credentials match the email and password you provided"
            raise AuthenticationFailed({"email": [err], "password": [err]})

        self.user = user
        # Raise Authentication Error if user is inactive
        if self.user.is_active is False:
            err = "You cannot log in to your account. Please contact admin for further assistance"
            raise AuthenticationFailed(err)

        # Update last login
        self.user.last_login = timezone.now()
        self.user.save()
        return self.user

    def login_and_get_tokens(self) -> dict[str, str]:
        self.login()
        refresh = RefreshToken.for_user(self.user)
        return {"refresh": refresh, "access": refresh.access_token}
    