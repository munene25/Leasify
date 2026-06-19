from typing import Any
from structlog import get_logger
from dataclasses import dataclass

logger = get_logger("payments.mpesa.callback")


@dataclass
class QueryResponse:
    """
    !Sample response:
    {
        "ResponseCode":"0",
        "ResponseDescription": "The service request has been accepted successfully",
        "MerchantRequestID":"22205-34066-1",
        "CheckoutRequestID": "ws_CO_13012021093521236557",
        "ResultCode":"0",
        "ResultDesc":"The service request is processed successfully.",
    }
    """

    checkout_id: str
    success: bool
    result_desc: str


def parse_query_response(response: dict[str, Any]) -> QueryResponse:
    """Parse a 'query payment status' request response"""
    data = response["Body"]["stkCallback"]

    return QueryResponse(
        checkout_id=data["CheckoutRequestID"],
        success=int(data["ResultCode"]) == 0,
        result_desc=data["ResultDesc"],
    )


@dataclass
class CallbackResponse:
    """
    !Sample failed data
    {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "f1e2-4b95-a71d-b30d3cdbb7a7942864",
                "CheckoutRequestID": "ws_CO_21072024125243250722943992",
                "ResultCode": 1032,
                "ResultDesc": "Request cancelled by user"
            }
        }
    }
    !Sample success data
    {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "29115-34620561-1",
                "CheckoutRequestID": "ws_CO_191220191020363925",
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {
                            "Name": "Amount",
                            "Value": 1.0
                        },
                        {
                            "Name": "MpesaReceiptNumber",
                            "Value": "NLJ7RT61SV"
                        },
                        {
                            "Name": "TransactionDate",
                            "Value": 20191219102115
                        },
                        {
                            "Name": "PhoneNumber",
                            "Value": 254708374149
                        }
                    ]
                }
            }
        }
    }
    """

    checkout_id: str
    success: bool
    result_desc: str
    receipt_no: str | None = None
    metadata: dict | None = None


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
