import requests
from config.settings import MPESA_CONFIG as cfg
from payments.mpesa.auth import get_access_token
from payments.mpesa.utils import make_timestamp, make_password
from payments.mpesa.types import STKPushResponse, QueryResponse


def initiate_stk_push(*, phone_number: str, amount: int, account_ref: str, description: str) -> STKPushResponse:
    """
    Transaction type: "CustomerPayBillOnline" for PayBill Numbers and "CustomerBuyGoodsOnline" for Till Numbers.
    """

    # There is a limit on the length of account ref or description
    if len(account_ref) > 12 or len(description) > 13:
        raise ValueError(f"Account_ref ({account_ref=}) or description ({description=}) too long")

    timestamp = make_timestamp()

    payload = {
        "Password": make_password(timestamp),
        "BusinessShortCode": cfg["SHORTCODE"],
        "Timestamp": timestamp,
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": cfg["SHORTCODE"],
        "TransactionType": "CustomerPayBillOnline",
        "PhoneNumber": phone_number,
        "TransactionDesc": description,
        "AccountReference": account_ref,
        "CallBackURL": cfg["INITIATE_URL"],
    }

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {get_access_token()}"}

    res = requests.post(cfg["EXPRESS_URL"], json=payload, headers=headers)
    res.raise_for_status()

    # Normalize and return response
    json = res.json()
    stk = STKPushResponse(json["CheckoutRequestID"], int(json["ResponseCode"]) == 0)
    return stk


def query_payment_status(checkout_request_id: str) -> QueryResponse:
    """Query the status of an M-PESA payment."""

    timestamp = make_timestamp()
    payload = {
        "BusinessShortCode": cfg["SHORTCODE"],
        "Password": make_password(timestamp),
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }
    # Make the API request to M-PESA
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {get_access_token()}"}

    res = requests.post(cfg["EXPRESS_URL"], json=payload, headers=headers)
    res.raise_for_status()

    # Parse and normalize response
    json_data = res.json()

    return QueryResponse(
        checkout_id=checkout_request_id,
        success=int(json_data["ResultCode"]) == 0,
        result_desc=json_data["ResultDesc"],
    )
