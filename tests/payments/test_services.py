import pytest
import requests
from datetime import date
from functools import partial
from unittest.mock import MagicMock
from structlog.types import EventDict
from rest_framework.exceptions import ValidationError, NotFound
from common.exceptions import MpesaAPIError
from tests.types import Factory
from users.models import User
from payments.models import Payment
from payments.choices import PaymentMode as PM, PaymentStatus as PS
from payments.services import payment_mpesa_query, payment_alt_create, payment_mpesa_initiate, payment_mpesa_process
from payments.mpesa import STKResult
from billing.models import BillingPeriod as BP
from billing.choices import BillingStatus as BS

class TestPaymentMpesaInitiate:
    def test_stk_push_called(self, monkeypatch: pytest.MonkeyPatch, billing_factory: Factory[BP]):
        """Mock and check stk push called with the correct details"""

        stk_push = MagicMock(return_value={"checkout_id": "ws_CO_12345"})

        timestamp = "20250101000000"
        monkeypatch.setattr("payments.services.initiate_stk_push", stk_push)
        monkeypatch.setattr("payments.services.make_timestamp", lambda: timestamp)

        # create a billing
        billing = billing_factory(statuses=[BS.UNPAID], starting=date(2025, 1, 1))[0]
        payment = payment_mpesa_initiate(billing=billing, phone_number="0700", idempotency_key="XYZ")
        assert payment is not None

        stk_push.assert_called_once_with(
            phone_number="0700",
            amount=int(billing.total_due),
            account_ref="JAN-2025",
            description="Rent Payment",
            timestamp=timestamp,
        )

    def test_protection_against_duplicate_payments(self, monkeypatch: pytest.MonkeyPatch, billing_factory: Factory[BP], payment_factory: Factory[Payment]):
        """
        Idempotency and Duplicate payments should not be allowed
        1. For billing that is already paid
        2. For a pending payment that is already underway.
        3. For a duplicate payment with the same idemp-key
        """
        billings = billing_factory(statuses=[BS.PAID, BS.CANCELLED, BS.UNPAID])

        monkeypatch.setattr("payments.services.initiate_stk_push", lambda: {"checkout_id": "unique_checkout"})
        initiate = partial(payment_mpesa_initiate, phone_number="0000")

        with pytest.raises(ValidationError, match="paid billing"):
            initiate(billing=billings[0], idempotency_key="XYZ1")

        with pytest.raises(ValidationError, match="cancelled billing"):
            initiate(billing=billings[1], idempotency_key="XYZ2")

        # For same idempotency key
        unpaid_billing = billing_factory(statuses=[BS.UNPAID])[0]
        processed = payment_factory(billing=unpaid_billing)[0]

        idemp_key = processed.idempotency_key
        assert idemp_key is not None

        assert initiate(idempotency_key=idemp_key, billing=processed.billing) == processed

        # For pending payment on billing
        pending = payment_factory(statuses=[PS.PENDING], billing=billings[2])[0]
        assert initiate(billing=billings[2], idempotency_key="XYZ3") == pending

    def test_stk_push_raises_exception(self, monkeypatch: pytest.MonkeyPatch, stk_callback_fail: dict, billing_factory: Factory[BP], caplog: list[EventDict]):
        """
        Cases where the stk initiation raises an error. 
        It should be caught, logged and raise an MPESA API error.
        """
        error = requests.exceptions.HTTPError("Something went wrong")
        error.response = MagicMock()
        error.response.json.return_value = stk_callback_fail
        error.response.status_code = 409
        
        raises = MagicMock(side_effect=error)
        monkeypatch.setattr("payments.services.initiate_stk_push", raises)

        billing = billing_factory(statuses=[BS.UNPAID])[0]

        with pytest.raises(MpesaAPIError, match="Service is unavailable"):
            payment_mpesa_initiate(billing=billing, phone_number="0000", idempotency_key="XYZ")
        assert Payment.objects.count() == 0 

        log = caplog[-1]
        assert log["event"] == "stk_push_failed"
        assert log["status_code"] == 409
        assert log["response"] == stk_callback_fail


    def test_query_count(self, monkeypatch: pytest.MonkeyPatch, django_assert_num_queries, billing_factory: Factory[BP]):
        """
        1. Strart transaction
        2. Lock billing
        3. Check for idemp key
        4. Check for pending
        5. Create payment
        6. End transaction
        """
        monkeypatch.setattr("payments.services.initiate_stk_push", lambda *args, **kwargs: {"checkout_id": "unique_checkout"})
        billing = billing_factory(statuses=[BS.UNPAID])[0]
        with django_assert_num_queries(6):
            payment_mpesa_initiate(billing=billing, phone_number="0000", idempotency_key="XYZ")

        

class TestPaymentAltCreate:
    def test_payment_created(self, billing_factory: Factory[BP], manager_user: User):
        """Should default to paid status"""
        billing = billing_factory(statuses=[BS.UNPAID])[0]
        payment = payment_alt_create(billing=billing, mode=PM.BANK, recorded_by=manager_user)
        assert payment.status == PS.SUCCESS
        assert payment.recorded_by == manager_user
        assert payment.payment_mode == PM.BANK
        assert billing.payments.filter(status="success").count() == 1
    
    def test_billing_needs_to_be_unpaid(self, billing_factory: Factory[BP], manager_user: User):
        """Should raise if billing period is paid or cancelled"""
        bills = billing_factory(statuses=[BS.PAID, BS.CANCELLED])
        
        with pytest.raises(ValidationError, match="cancelled"):
            payment_alt_create(billing=bills[1], mode=PM.CASH, recorded_by=manager_user)

        with pytest.raises(ValidationError, match="paid"):
            payment_alt_create(billing=bills[0], mode=PM.BANK, recorded_by=manager_user)
    
    def test_number_of_queries(self, django_assert_num_queries, billing_factory: Factory[BP], manager_user: User):
        """
        1. Creating the payment
        """
        bill = billing_factory(statuses=[BS.UNPAID])[0]
        with django_assert_num_queries(1):
            payment_alt_create(billing=bill, recorded_by=manager_user, mode=PM.CASH)
        
class TestPaymentMpesaProcess:
    def test_payment_update_based_on_result(self, monkeypatch: pytest.MonkeyPatch, payment_factory: Factory[Payment], stk_result):
        "A payment needs to be updated to success or fail based on stk_result"
        
        monkeypatch.setattr("payments.tasks.send_payment_notification.delay", lambda *args: None)
        pending = payment_factory(statuses=[PS.PENDING, PS.PENDING])
        stk_result_success = stk_result(True, pending[0].checkout_id)
        stk_result_failed = stk_result(False, pending[1].checkout_id)

        # Successful Payment
        payment = payment_mpesa_process(stk_result_success)
        assert payment == pending[0]
        payment.refresh_from_db()
        assert payment.status == PS.SUCCESS
        assert payment.receipt_no == stk_result_success["receipt_no"]

        # For failed payment
        payment2 = payment_mpesa_process(stk_result_failed)
        assert payment2 == pending[1]
        payment2.refresh_from_db()
        assert payment2.status == PS.FAILED
        assert payment2.receipt_no == None


    def test_checkout_not_found_raises(self, stk_result):
        """It should raise a not found"""
        with pytest.raises(NotFound, match="checkout_id does not exist"):
            payment_mpesa_process(stk_result(False))

    def test_extra_recepients_called(self, monkeypatch: pytest.MonkeyPatch, pending_payment: Payment, stk_result):
        """Extra recepients should be called"""
        mock = MagicMock()
        monkeypatch.setattr("payments.selectors.payment_get_extra_recepients", mock)
        
        # mock to avoid sending email
        monkeypatch.setattr("payments.tasks.send_payment_notification.delay", lambda *args: None)
        stk_result_success = stk_result(True, pending_payment.checkout_id)
        payment_mpesa_process(stk_result_success)
        mock.assert_called_once()

    def test_sending_notification_called(self, manager_user: User, monkeypatch: pytest.MonkeyPatch, pending_payment: Payment, stk_result):
        """Notification task should be called with the correct parameters"""
        patch_notify = MagicMock()
        monkeypatch.setattr("payments.tasks.send_payment_notification.delay", patch_notify)
    
        stk_result_success = stk_result(True, pending_payment.checkout_id)
        
        payment_mpesa_process(stk_result_success)
        patch_notify.assert_called_once_with(pending_payment.pk, [manager_user.email])

    def test_no_queries(self, monkeypatch: pytest.MonkeyPatch, pending_payment: Payment, stk_result, django_assert_num_queries):
        """
        1. Get checkout
        2. Update payment status
        3. Get extra recepients
        4. Get payment in delayed task[Optional]
        """
        monkeypatch.setattr("payments.tasks.send_payment_notification.delay", lambda *args, **kwargs: None)
        with django_assert_num_queries(3):
            payment_mpesa_process(stk_result=stk_result(False, pending_payment.checkout_id))

class TestPaymentMpesaQuery:
    def test_raises_for_non_mpesa_queries(self, payment_factory: Factory[Payment]):
        """Non Mpesa payments should raise validation Errors"""
        payment = payment_factory(payment_mode=PM.CASH)[0]
        with pytest.raises(ValidationError, match="M-PESA"):
            payment_mpesa_query(payment)        

    def test_query_count(self, payment_factory: Factory[Payment], django_assert_num_queries):
        """Based on the type of payment, Either calls made in payment processing or none"""
        payments = payment_factory(statuses=[PS.SUCCESS])
        with django_assert_num_queries(0):
            payment_mpesa_query(payments[0])
    
    def test_stk_query_called_once_with_correct_params(self, monkeypatch: pytest.MonkeyPatch, pending_payment: Payment, stk_result):
        """The kwargs should be the checkout_id and timestamp"""
        result = stk_result(True, pending_payment.checkout_id)
        mock = MagicMock(return_value=result)
        monkeypatch.setattr("payments.services.query_payment_status", mock)
        payment = payment_mpesa_query(pending_payment)
        assert payment == pending_payment
        mock.assert_called_with(
            checkout_id=pending_payment.checkout_id,
            timestamp=pending_payment.timestamp
        )

    def test_stk_fails(self, monkeypatch: pytest.MonkeyPatch, pending_payment: Payment, caplog):
        """If fails, it should throw an MPESA API Error and log the error"""
        exception = requests.exceptions.Timeout()
        exception.response = MagicMock()
        exception.response.status_code = 409
        message = {"ResponseCode": "409"}
        exception.response.json.return_value = message
        mock = MagicMock(side_effect=exception)
        monkeypatch.setattr("payments.services.query_payment_status", mock)

        with pytest.raises(MpesaAPIError, match="Service is unavailable"):
            payment_mpesa_query(pending_payment)
        
        pending_payment.refresh_from_db()
        assert pending_payment.status == PS.PENDING

        log = caplog[-1]
        assert log["event"] == "payment_query_failed"
        assert log["status_code"] == 409
        assert log["response"] == message

    def test_payment_mpesa_process_called_and_return_value(self, monkeypatch: pytest.MonkeyPatch, pending_payment: Payment, stk_result):
        """Should return a payment, after calling process"""
        stk = stk_result(True, pending_payment.checkout_id)
        mock_query = MagicMock(return_value = stk)
        mock_payment_process = MagicMock()
        monkeypatch.setattr("payments.services.query_payment_status", mock_query)
        monkeypatch.setattr("payments.services.payment_mpesa_process", mock_payment_process)

        payment_mpesa_query(pending_payment)
        mock_payment_process.assert_called_once_with(stk)
