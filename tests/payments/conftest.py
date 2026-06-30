import pytest
from unittest.mock import MagicMock

@pytest.fixture
def stk_callback_fail():
    return {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "f1e2-4b95-a71d-b30d3cdbb7a7942864",
                "CheckoutRequestID": "ws_CO_12345",
                "ResultCode": 1032,
                "ResultDesc": "Request cancelled by user",
            }
        }
    }


@pytest.fixture
def stk_callback_sucess():
    return {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "29115-34620561-1",
                "CheckoutRequestID": "ws_CO_12345",
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 1.0},
                        {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SV"},
                        {"Name": "TransactionDate", "Value": 20191219102115},
                        {"Name": "PhoneNumber", "Value": 254708374149},
                    ]
                },
            }
        }
    }


@pytest.fixture
def stk_query_success():
    return {
        "ResponseCode": "0",
        "ResponseDescription": "The service request has been accepted successfully",
        "MerchantRequestID": "22205-34066-1",
        "CheckoutRequestID": "ws_CO_12345",
        "ResultCode": "0",
        "ResultDesc": "The service request is processed successfully.",
    }


@pytest.fixture
def stk_initial_response():
    return {
        "MerchantRequestID": "2654-4b64-97ff-b827b542881d3130",
        "CheckoutRequestID": "ws_CO_12345",
        "ResponseCode": "0",
        "ResponseDescription": "Success. Request accepted for processing",
        "CustomerMessage": "Success. Request accepted for processing",
    }


@pytest.fixture
def patch_mpesa_auth(monkeypatch: pytest.MonkeyPatch):
    mock = MagicMock(return_value="secret_token")
    monkeypatch.setattr("payments.mpesa.auth.get_access_token", mock)
    yield mock