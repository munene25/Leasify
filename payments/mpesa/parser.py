from payments.mpesa.types import CallbackResponse

def parse_callback_response(response: dict) -> CallbackResponse:
    """Parse the M-PESA callback response.

    :param response: The raw callback response dictionary
    :return: CallbackResponse object with checkout_id, success, result_desc, receipt_no, and metadata
    """
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
