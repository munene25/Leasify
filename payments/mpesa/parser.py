from typing import Any
import requests
from payments.mpesa.types import STKResult


def parse_callback_response(response: dict[str, Any]) -> STKResult:
    """Parse the M-PESA callback response.

    :param response: The raw callback response dictionary
    :return: CallbackResponse object with checkout_id, success, result_desc, receipt_no, and metadata
    """
    data = response["Body"]["stkCallback"]
    metadata = {"merchant_id": data["MerchantRequestID"]}

    cb: STKResult = {
        "checkout_id": data["CheckoutRequestID"],
        "success": int(data["ResultCode"]) == 0,
        "result_desc": data["ResultDesc"],
        "metadata": metadata,
        "receipt_no": None,
    }

    try:
        meta = {item["Name"]: item["Value"] for item in data["CallbackMetadata"]["Item"]}
        cb["receipt_no"] = meta.pop("MpesaReceiptNumber")
        cb["metadata"].update(meta)
    except KeyError:
        pass
    return cb


def parse_error(error: requests.exceptions.RequestException) -> tuple[int | None, dict | str | None]:
    """Parses request exceptions to extract data for logging"""
    response = getattr(error, "response", None)
    if response:
        status: int = response.status_code
        try:
            message: str | dict = response.json()
        except AttributeError:
            message = str(response)
        return status, message
    else:
        return None, None
