import pytest


@pytest.fixture
def stk_callback_fail():
    return {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "f1e2-4b95-a71d-b30d3cdbb7a7942864",
                "CheckoutRequestID": "ws_CO_21072024125243250722943992",
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
                "CheckoutRequestID": "ws_CO_191220191020363925",
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
        "CheckoutRequestID": "ws_CO_13012021093521236557",
        "ResultCode": "0",
        "ResultDesc": "The service request is processed successfully.",
    }


@pytest.fixture
def stk_initial_response():
    return {
        "MerchantRequestID": "2654-4b64-97ff-b827b542881d3130",
        "CheckoutRequestID": "ws_CO_1007202409152617172396192",
        "ResponseCode": "0",
        "ResponseDescription": "Success. Request accepted for processing",
        "CustomerMessage": "Success. Request accepted for processing",
    }
