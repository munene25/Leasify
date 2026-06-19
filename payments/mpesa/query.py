import requests
from config.settings import MPESA_CONFIG as cfg
from payments.mpesa.authenticate import get_access_token
from dataclasses import dataclass
from payments.mpesa.utils import make_timestamp, make_password


@dataclass
class QueryResponse:
    """
    M-PESA Query Response

    Sample response structure from the API:
    {
        "ResponseCode": "0",
        "ResponseDescription": "The service request has been accepted successfully",
        "MerchantRequestID": "22205-34066-1",
        "CheckoutRequestID": "ws_CO_13012021093521236557",
        "ResultCode": "0",
        "ResultDesc": "The service request is processed successfully.",
    }
    """

    checkout_id: str
    success: bool
    result_desc: str


def query_payment_status(checkout_request_id: str) -> QueryResponse:
    """Query the status of an M-PESA STK push payment."""

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
