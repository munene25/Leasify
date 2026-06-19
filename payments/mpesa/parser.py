from typing import Any
from payments.mpesa.types import CallbackResponse

def parse_callback_response(response: dict[str, Any]) -> CallbackResponse:
    """Helper to parse the response body for the Mpesa"""
    data = response["Body"]["stkCallback"]
    metadata = {"merchant_id": data["MerchantRequestID"]}

    cb = CallbackResponse(
        checkout_id=data["CheckoutRequestID"],
        success=int(data["ResultCode"]) == 0,
        result_desc=data["ResultDesc"],
        metadata=metadata,
    )
    try:cb.receipt_no = metadata["MpesaReceiptNumber"]
    except KeyError: pass
    return cb
