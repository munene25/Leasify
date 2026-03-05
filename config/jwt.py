from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from typing import override, Tuple, Any

class JWTCookieAuthentication(JWTAuthentication):
    """Authentication class with simple JWT. **CSRF Exempt**"""
    @override
    def authenticate(self, request: Request) -> Tuple[AbstractUser, dict[str, Any]] | None :
        token_name = settings.COOKIE_SETTINGS["AUTH_COOKIE"]
        raw_token = request.COOKIES.get(token_name, None)
        if raw_token is None:
            return None
        token = self.get_validated_token(raw_token)
        u = self.get_user(token)
        return u, {"type": "jwt", "token": token}
