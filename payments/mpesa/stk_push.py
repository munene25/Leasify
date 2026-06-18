import base64
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from config.settings import MPESA_CONFIG as cfg
from payments.mpesa.authenticate import get_access_token
from structlog import get_logger
from dataclasses import dataclass

logger = get_logger("payments.mpesa.stk_push")


@dataclass
class STKPushResponse:
    checkout_id: str
    sucess: bool
    

def initiate_stk_push(*, phone_number: str, amount: int, account_ref: str, description: str) -> STKPushResponse:
    """
    Transaction type: "CustomerPayBillOnline" for PayBill Numbers and "CustomerBuyGoodsOnline" for Till Numbers.
    """

    # There is a limit on the length of account ref or description
    if len(account_ref) > 12 or len(description) > 13:
        raise ValueError(f"Account_ref ({account_ref=}) or description ({description=}) too long")

    # Compute current time at UTC + 3
    nairobi = ZoneInfo("Africa/Nairobi")
    dt = datetime.now(tz=nairobi)
    timestamp = dt.strftime("%Y%m%H%d%M%S")

    access_token = get_access_token()
    password_bytes = (cfg["SHORTCODE"] + cfg["PASSKEY"] + timestamp).encode()

    payload = {
        "Password": base64.b64encode(password_bytes).decode(),
        "BusinessShortCode": cfg["SHORTCODE"],
        "Timestamp": timestamp,
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": cfg["SHORTCODE"],
        "TransactionType": "CustomerPayBillOnline",
        "PhoneNumber": phone_number,
        "TransactionDesc": description,
        "AccountReference": "Test",
        "CallBackURL": "https://mydomain.com/mpesa-express-simulate/",
    }

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}

    res = requests.post(cfg["EXPRESS_URL"], json=payload, headers=headers)
    res.raise_for_status()

    # Normalize and return response
    json = res.json()
    stk = STKPushResponse(json["CheckoutRequestID"], int(json["ResponseCode"]) == 0)
    
    logger.info(
        "stk_push_initiated",
        checkout_id=stk.checkout_id,
    )
    return stk


# Sample response
# {
#   "MerchantRequestID": "2654-4b64-97ff-b827b542881d3130",
#   "CheckoutRequestID": "ws_CO_1007202409152617172396192",
#   "ResponseCode": "0",
#   "ResponseDescription": "Success. Request accepted for processing",
#   "CustomerMessage": "Success. Request accepted for processing"
# }
