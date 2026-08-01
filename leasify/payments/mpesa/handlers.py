import requests
from django.conf import settings
from leasify.payments.mpesa import STKInitialResponse, STKResult, auth
from leasify.payments.mpesa import utils

cfg = settings.MPESA

def initiate_stk_push(phone_number: str, amount: int, account_ref: str, description: str, timestamp: str, callback_url: str) -> STKInitialResponse:
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
    if (acc := len(account_ref) > 12) or len(description) > 13:
        error = f"Account Reference ({account_ref})" if acc else f"Description ({description})"
        raise ValueError(f"{error} too long")

    payload = {
        "Password": utils.make_password(cfg["SHORTCODE"], cfg["PASSKEY"], timestamp),
        "BusinessShortCode": cfg["SHORTCODE"],
        "Timestamp": timestamp,
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": cfg["SHORTCODE"],
        "TransactionType": "CustomerPayBillOnline",
        "PhoneNumber": phone_number,
        "TransactionDesc": description,
        "AccountReference": account_ref,
        "CallBackURL": callback_url,
    }

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {auth.get_access_token()}"}

    res = requests.post(cfg["INITIATE_URL"], json=payload, headers=headers)
    res.raise_for_status()

    # Normalize and return response
    json = res.json()
    return {"checkout_id": json["CheckoutRequestID"], "success": int(json["ResponseCode"]) == 0}


def query_payment_status(checkout_id: str, timestamp: str) -> STKResult:
    """Query the status of an M-PESA payment.

    :param checkout_request_id: The M-PESA CheckoutRequestID from the STK push response
    :param timestamp: The timestamp for the payment in strftime
    :return: QueryResponse object with checkout_id, success, and result_desc
    """
    payload = {
        "BusinessShortCode": cfg["SHORTCODE"],
        "Password": utils.make_password(cfg["SHORTCODE"], cfg["PASSKEY"], timestamp),
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_id,
    }
    # Make the API request to M-PESA
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {auth.get_access_token()}"}

    res = requests.post(cfg["QUERY_URL"], json=payload, headers=headers)
    res.raise_for_status()

    # Parse and normalize response
    json = res.json()

    return {
        "checkout_id": checkout_id,
        "success": int(json["ResultCode"]) == 0,
        "result_desc": json["ResultDesc"],
        "metadata": {"merchant_id": json["MerchantRequestID"]},
        "receipt_no": None,
    }
