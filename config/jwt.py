from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import HTTP_HEADER_ENCODING

class JWTCookieAuthenticator(JWTAuthentication):
    def authenticate(self, request: Request) -> tuple | None:
        token = request.COOKIES.get('access')
        if not token:
            return None
        token = token.encode(HTTP_HEADER_ENCODING)
        validated_token = self.get_validated_token(token)
        return (self.get_user(validated_token), validated_token)