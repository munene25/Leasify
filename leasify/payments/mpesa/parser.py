from typing import Any
import requests

from leasify.payments.mpesa.types import STKResult


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


def parse_error(error: requests.exceptions.RequestException) -> tuple[int | None, dict , str]:
    """Parse a requests exception into a status code error_log message."""

    status: int | None = None
    err: dict =  {"error": str(error)}
    outbound: str = "Service is unavailable at the moment. Please try again later."

    response: requests.Response | None = getattr(error, "response", None)

    if  response is not None:
        status = response.status_code

        try:
            payload = response.json()
            if isinstance(payload, dict):
                err = payload

                if errorMessage := payload.get("errorMessage"):
                    outbound = errorMessage

            else:
                err = {"error": payload}

        except (requests.JSONDecodeError):
            err = {"error_text": response.text}

    return status, err, outbound
