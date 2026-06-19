import requests
from config.settings import MPESA_CONFIG as cfg
from payments.mpesa.auth import get_access_token
from payments.mpesa.utils import make_timestamp, make_password
from payments.mpesa.types import STKPushResponse, STKResult


def initiate_stk_push(phone_number: str, amount: int, account_ref: str, description: str) -> STKPushResponse:
    """Initiate a M-PESA STK push request.

    Transaction type is "CustomerPayBillOnline" for PayBill Numbers and "CustomerBuyGoodsOnline" for Till Numbers.

    :param phone_number: Phone number of the customer
    :param amount: Amount to pay in shillings
    :param account_ref: Account reference or bill number (max 12 chars)
    :param description: Payment description (max 13 chars)
    :return: STKPushResponse object with checkout_id and success status

    Raises ValueError if account_ref exceeds 12 characters or description exceeds 13 characters.
    """

    # There is a limit on the length of account ref or description
    if len(account_ref) > 12 or len(description) > 13:
        raise ValueError(f"Account_ref ({account_ref}) or description ({description}) too long")

    timestamp = make_timestamp()

    payload = {
        "Password": make_password(cfg["SHORTCODE"], cfg["PASSKEY"], timestamp),
        "BusinessShortCode": cfg["SHORTCODE"],
        "Timestamp": timestamp,
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": cfg["SHORTCODE"],
        "TransactionType": "CustomerPayBillOnline",
        "PhoneNumber": phone_number,
        "TransactionDesc": description,
        "AccountReference": account_ref,
        "CallBackURL": cfg["CALLBACK_URL"],
    }

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {get_access_token()}"}

    res = requests.post(cfg["INITIATE_URL"], json=payload, headers=headers)
    res.raise_for_status()

    # Normalize and return response
    json = res.json()
    stk = STKPushResponse(json["CheckoutRequestID"], int(json["ResponseCode"]) == 0)
    return stk


def query_payment_status(checkout_request_id: str) -> STKResult:
    """Query the status of an M-PESA payment.

    :param checkout_request_id: The M-PESA CheckoutRequestID from the STK push response
    :return: QueryResponse object with checkout_id, success, and result_desc
    """

    timestamp = make_timestamp()
    payload = {
        "BusinessShortCode": cfg["SHORTCODE"],
        "Password": make_password(cfg["SHORTCODE"], cfg["PASSKEY"], timestamp),
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }
    # Make the API request to M-PESA
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {get_access_token()}"}

    res = requests.post(cfg["QUERY_URL"], json=payload, headers=headers)
    res.raise_for_status()

    # Parse and normalize response
    json_data = res.json()

    return STKResult(
        checkout_id=checkout_request_id,
        success=int(json_data["ResultCode"]) == 0,
        result_desc=json_data["ResultDesc"],
    )
