from rest_framework.response import Response

class UserCookiesMixin:
    def _set_cookies(self, *, response: Response, **kwargs):
        for key, val in kwargs.items():
            response.set_cookie(
                key=key,
                value=val,
                httponly=True,
                secure=False,
                samesite="Lax",
            )

    def _del_cookies(self, *args, response: Response):
        for arg in args:
            response.delete_cookie(arg)
