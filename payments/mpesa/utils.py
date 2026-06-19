import base64
from datetime import datetime
from zoneinfo import ZoneInfo
from config.settings import MPESA_CONFIG as cfg

def make_password(timestamp: str):
    """"""
    password_bytes = (cfg["SHORTCODE"] + cfg["PASSKEY"] + timestamp).encode()
    return base64.b64encode(password_bytes).decode()

def make_timestamp() -> str:
    """"""
    nairobi = ZoneInfo("Africa/Nairobi")
    dt = datetime.now(tz=nairobi)
    return dt.strftime("%Y%m%H%d%M%S")