from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework_simplejwt.exceptions import InvalidToken
from users.models import User
from .selectors import user_get_by_id
from django.conf import settings


def token_url_generate(user: User, path: str) -> str:
    uuid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    base_url = getattr(settings, "SITE_URL",)
    if base_url is None:
        raise RuntimeError("SITE_URL not configured in settings")
    return f"{base_url}/{path}/{uuid}/{token}"


def token_validate(*, uuid: str, token: str) -> User:
    try:
        user_id = force_str(urlsafe_base64_decode(uuid))
        user = user_get_by_id(int(user_id))
        if default_token_generator.check_token(user, token):
            return user
        raise Exception
    except Exception:
        raise InvalidToken()


def unsubscribe_url_for(user: User):
    uuid = urlsafe_base64_encode(force_bytes(user.pk))
    base_url = getattr(settings, "SITE_URL")
    return f"{base_url}/unsubscribe/{uuid}"

def unsubscribe_token_validate(uuid) -> User:
    try:
        user_id = force_str(urlsafe_base64_decode(uuid))
        user = user_get_by_id(int(user_id))
        return user
    except Exception:
        raise InvalidToken()