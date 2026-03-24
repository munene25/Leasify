from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from common.exceptions import UserLinkMalformed
from users.models import User
from users.selectors import user_get

BASE_URL: str = getattr(settings, "FRONTEND_URL")

def build_user_url(*, user: User, path: str, with_token: bool = True) -> str:
    """
    Constructs a URL pointing to the frontend for user-specific actions.
    Token can be ommited for non sensitive tasks.
    """
    segments = [BASE_URL, path, uidb64_generate(user)]
    if with_token:
        segments.append(token_generate(user))

    return  "/".join(seg for seg in segments)


def token_generate(user: User)-> str:
    """create a one time user token for a user"""
    return default_token_generator.make_token(user)

def token_validate(*, user: User, token: str) -> None:
    """Check provided token for expiry and validity"""
    if not default_token_generator.check_token(user, token):
        raise UserLinkMalformed() 

def uidb64_generate(user: User) -> str:
    """Returns the user_id as a base 64 encoded string"""
    return urlsafe_base64_encode(force_bytes(user.pk))

def get_user_from_uidb64(uidb64: str) -> User:
    """Decode base 64 encoded string and get the associated user"""
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        return user_get(int(user_id))
    except ValueError:
        raise UserLinkMalformed()