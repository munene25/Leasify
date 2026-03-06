from rest_framework.response import Response
from django.conf import settings


class CookieMixin:
    def set_cookies(self, *, response: Response, **kwargs) -> Response:
        cookies = settings.COOKIE_SETTINGS

        for key, value in kwargs.items():
            response.set_cookie(
                key=key,
                value=value,
                httponly=cookies["AUTH_COOKIE_HTTP_ONLY"],
                secure=cookies["AUTH_COOKIE_SECURE"],
                samesite=cookies["AUTH_COOKIE_SAMESITE"],
                domain=cookies["AUTH_COOKIE_DOMAIN"],
                path=cookies["AUTH_COOKIE_PATH"],
            )
        return response

    def del_cookies(self, *, cookies: list[str], response: Response) -> Response:
        for arg in cookies:
            response.delete_cookie(arg)
        return response
