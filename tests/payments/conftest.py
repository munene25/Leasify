import pytest
import typing
from unittest.mock import MagicMock
from payments.mpesa import STKResult
from payments.models import Payment
from payments.choices import PaymentStatus as PS
from tests.types import Factory

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

@pytest.fixture(scope="session")
def stk_result() -> typing.Callable[[bool, str], STKResult]:
    """Return an stk result dict for for either success or failed based on a checkout_id"""

    def stk_from_payment(success: bool, checkout_id: str | None = None) -> STKResult:
        return {
            "checkout_id": checkout_id or "ws_CO_1234",
            "receipt_no": "RCPT-1234" if success else None,
            "result_desc": "Payment successful" if success else "Payment could not be completed",
            "success": success,
            "metadata": {"merchant_id": "MERCHANT-1234"},
        }

    return stk_from_payment

@pytest.fixture
def pending_payment(payment_factory: Factory[Payment]) -> Payment:
    "Returns a pending payment"
    return payment_factory(statuses=[PS.PENDING])[0]

@pytest.fixture()
def patch_payment_get_for(monkeypatch: pytest.MonkeyPatch, payment_factory: Factory[Payment]):
    billing = payment_factory(1, statuses=[PS.SUCCESS])[0]
    mock = MagicMock(return_value=billing)
    monkeypatch.setattr("payments.selectors.payment_get_for", mock)
    yield mock


@pytest.fixture
def patch_payment_mpesa_initiate(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    mock.return_value.pk = 1
    monkeypatch.setattr("payments.services.payment_mpesa_initiate", mock)
    return mock

@pytest.fixture
def patch_payment_mpesa_process_async(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    mock.delay = MagicMock(return_value=None)
    monkeypatch.setattr("payments.tasks.payment_mpesa_process_async", mock)
    return mock

@pytest.fixture
def patch_payment_mpesa_query(monkeypatch: pytest.MonkeyPatch, stk_result) -> MagicMock:
    mock = MagicMock(return_value=stk_result(True, None))
    monkeypatch.setattr("payments.services.payment_mpesa_query", mock)
    return mock