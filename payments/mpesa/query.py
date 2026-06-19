from typing import Any
from config.settings import MPESA_CONFIG as cfg
from payments.mpesa.authenticate import get_access_token
from structlog import get_logger
from dataclasses import dataclass


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

