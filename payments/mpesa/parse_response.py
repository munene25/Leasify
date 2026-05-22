from typing import Any
from structlog import get_logger
from dataclasses import dataclass

logger = get_logger("payments.mpesa.callback")


@dataclass
class CallbackResponse:
    checkout_id: str
    success: bool
    result_desc: str
    receipt_no: str| None = None


def parse_response(response: dict[str, Any]) -> CallbackResponse:
    data = response["Body"]["stkCallback"]

    metadata = {"merchant_id": data["MerchantRequestID"]}

    callback = CallbackResponse(
        checkout_id=data["CheckoutRequestID"],
        success=int(data["ResultCode"]) == 0,
        result_desc=data["ResultDesc"],
    )

    if callback.success:
        try:
            metadata.update(
                {
                    item["Name"]: item.get("Value") 
                    for item in data["CallbackMetadata"]["Item"]
                }
            )

            callback.receipt_no = metadata["MpesaReceiptNumber"]

        except KeyError as e:
            logger.debug("failed_to_parse_payment_metadata", error=str(e))

    logger.info(
        "response_parsed", 
        checkout_id=callback.checkout_id, 
        sucess=callback.success,
        result_desc=callback.result_desc,
        metadata=str(metadata)
    )
    return callback


# Sample failed data
# {
#   "Body": {
#     "stkCallback": {
#       "MerchantRequestID": "f1e2-4b95-a71d-b30d3cdbb7a7942864",
#       "CheckoutRequestID": "ws_CO_21072024125243250722943992",
#       "ResultCode": 1032,
#       "ResultDesc": "Request cancelled by user"
#     }
#   }
# }


# Sample success data
# {
#   "Body": {
#     "stkCallback": {
#       "MerchantRequestID": "29115-34620561-1",
#       "CheckoutRequestID": "ws_CO_191220191020363925",
#       "ResultCode": 0,
#       "ResultDesc": "The service request is processed successfully.",
#       "CallbackMetadata": {
#         "Item": [
#           {
#             "Name": "Amount",
#             "Value": 1.0
#           },
#           {
#             "Name": "MpesaReceiptNumber",
#             "Value": "NLJ7RT61SV"
#           },
#           {
#             "Name": "TransactionDate",
#             "Value": 20191219102115
#           },
#           {
#             "Name": "PhoneNumber",
#             "Value": 254708374149
#           }
#         ]
#       }
#     }
#   }
# }
