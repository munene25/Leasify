from rest_framework.response import Response
from django.conf import settings
from functools import cached_property


class CookiesMixin:
    @cached_property
    def cookie_settings(self):
        return settings.COOKIE_SETTINGS

    def set_cookies(self, *, response: Response, **kwargs) -> Response:
        cookies = self.cookie_settings
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

    def del_cookies(self, *args, response: Response) -> Response:
        for arg in args:
            response.delete_cookie(arg)
        return response
