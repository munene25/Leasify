from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from rest_framework.exceptions import NotFound

from leasify.common.exceptions import UserLinkMalformedError
from leasify.users.models import User
from leasify.users.selectors import user_get

BASE_URL: str = getattr(settings, "FRONTEND_URL")

def build_url(*, base_path, with_uidb64, with_token, user: User | None = None) -> str:
    """Construct URLS pointing to the frontend"""
    segments = [BASE_URL, base_path]
    if with_token or with_uidb64:
        if not user:
            raise ValueError("User not Provided")
        if with_uidb64:
            segments.append(uidb64_generate(user))
        if with_token:
            segments.append(token_generate(user))

    return "/".join(segments)

def token_generate(user: User) -> str:
    """Create a one time use token for a user"""
    return default_token_generator.make_token(user)


def token_validate(*, user: User, token: str) -> None:
    """Check provided token for expiry and validity"""
    if not default_token_generator.check_token(user, token):
        raise UserLinkMalformedError()


def uidb64_generate(user: User) -> str:
    """Returns the user_id as a base 64 encoded string"""
    return urlsafe_base64_encode(force_bytes(user.pk))


def get_user_from_uidb64(uidb64: str) -> User:
    """Decode base 64 encoded string and get the associated user"""
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        return user_get(int(user_id))
    except (ValueError, NotFound):
        raise UserLinkMalformedError()
