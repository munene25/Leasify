from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings


class JWTCookieAuthentication(JWTAuthentication):
    """Authentication class with simple JWT. **CSRF Exempt**"""

    def authenticate(self, request: Request):
        token_name = settings.COOKIE_SETTINGS["AUTH_COOKIE"]
        raw_token = request.COOKIES.get(token_name, None)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        if not user.is_active:
            return None
        return user, {"type": "jwt", "token": validated_token}
