import base64
from datetime import datetime
from zoneinfo import ZoneInfo
from config.django.base import MPESA_CONFIG as cfg


def make_password(shortcode: str, passkey: str, timestamp: str) -> str:
    """Generate the M-PESA password for API requests.

    :param shortcode: The business short code
    :param passkey: The M-PESA passkey
    :param timestamp: Timestamp string in YYYYMMDDHHmmSS format
    :return: Base64 encoded password string
    """
    password_bytes = (shortcode + passkey + timestamp).encode()
    return base64.b64encode(password_bytes).decode()


def make_timestamp() -> str:
    """Generate a timestamp in M-PESA format.

    :return: Timestamp string in YYYYMMDDHHmmSS format
    """
    nairobi = ZoneInfo("Africa/Nairobi")
    dt = datetime.now(tz=nairobi)
    return dt.strftime("%Y%m%d%H%M%S")
