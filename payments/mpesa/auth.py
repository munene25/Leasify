import requests
from requests.auth import HTTPBasicAuth
from config.settings import MPESA_CONFIG as cfg
from structlog import get_logger
from django.core.cache import cache

logger = get_logger("payments.mpesa.auth")


def get_access_token() -> str:
    """Get access token for M-PESA express API authentication.

    Fetches from cache first, then authenticates with provider on cache miss.
    Tokens are cached for 55 minutes (token expiry is typically 1 hour).

    :return: Access token string
    """

    cache_key = "mpesa_access_token"
    token = cache.get(cache_key)
    if token:
        return token

    res = requests.get(cfg["AUTHENTICATE_URL"], auth=HTTPBasicAuth(cfg["CONSUMER_KEY"], cfg["CONSUMER_SECRET"]))
    res.raise_for_status()
    token = res.json()["access_token"]
    cache.set(cache_key, token, timeout=60 * 55)

    return token
