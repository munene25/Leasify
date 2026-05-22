import requests
from requests.auth import HTTPBasicAuth
from config.settings import MPESA_CONFIG as cfg
from structlog import get_logger

logger = get_logger("payments.mpesa.auth")


def get_access_token() -> str:
    """
    Get access token for mpesa express authentication.
    Tries to fetch from cache first and defaults to a authentication request to payment provider.
    On authentciation request, cache the key for 55 mins, as the token expiry is usually 1hr
    """
    from django.core.cache import cache

    cache_key = "mpesa_access_token"
    token = cache.get(cache_key)
    if token:
        return token

    res = requests.get(
        url=cfg["AUTHENTICATE_URL"], 
        auth=HTTPBasicAuth(cfg["CONSUMER_KEY"], 
        cfg["CONSUMER_SECRET"])
    )
    res.raise_for_status()

    logger.info("mpesa_auth_successful")
    
    token = res.json()["access_token"]
    cache.set(cache_key, token, timeout=60 * 55)

    return token
