import pytest
import requests
from datetime import date
from unittest.mock import MagicMock
from rest_framework.exceptions import ValidationError
from common.exceptions import MpesaAPIError
from tests.types import Factory
from users.models import User
from payments.models import Payment
from payments.choices import PaymentMode as PM, PaymentStatus as PS
from payments.services import payment_mpesa_query, payment_alt_create, payment_mpesa_initiate, payment_mpesa_process
from billing.models import BillingPeriod as BP
from billing.choices import BillingStatus as BS
from functools import partial
from structlog.types import EventDict

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