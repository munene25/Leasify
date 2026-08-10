from typing import Mapping, Any

from structlog import get_logger

from django.conf import settings
from rest_framework.exceptions import ValidationError

from google.oauth2 import id_token
from google.auth import exceptions
from google.auth.transport import requests as g_requests


logger = get_logger("auth.google")

def verify_claims(token: str) -> Mapping[str, Any]:
    """
    Verify token with Google. 
    Catches  GoogleAuthError or ValueError
    """
    try: 
        claims = id_token.verify_oauth2_token(
            token,
            g_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except (exceptions.GoogleAuthError, ValueError) as e:
        logger.error("google_auth_failed", error=str(e))
        raise ValidationError("Google authentication failed. Try again")

    # Normalize
    user_data = {
        "provider_id": claims["sub"],
        "email": claims["email"],
        "first_name": claims.get("given_name", " "),
        "last_name": claims.get("family_name", claims.get("given_name", " ")),
    }


    logger.info("google_auth_success", claims=claims)
    return user_data 
