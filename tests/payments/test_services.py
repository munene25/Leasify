import pytest
from datetime import date
from unittest.mock import MagicMock
from rest_framework.exceptions import ValidationError
from tests.types import Factory
from payments.models import Payment
from payments.choices import PaymentMode as PM, PaymentStatus as PS
from payments.services import payment_mpesa_query, payment_alt_create, payment_mpesa_initiate, payment_mpesa_process
from billing.models import BillingPeriod as BP
from billing.choices import BillingStatus as BS
from functools import partial

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
        
        monkeypatch.setattr("payments.services.initiate_stk_push", {"checkout_id": "unique_checkout"})
        initiate = partial(payment_mpesa_initiate, phone_number="0000")

        with pytest.raises(ValidationError, match="paid billing"):
            initiate(billing=billings[0], idempotency_key="XYZ1")

        with pytest.raises(ValidationError, match="cancelled billing"):
            initiate(billing=billings[1],  idempotency_key="XYZ2")
        
        # For same idempotency key
        unpaid_billing = billing_factory(statuses=[BS.UNPAID])[0]
        processed = payment_factory(billing=unpaid_billing)[0]

        idemp_key = processed.idempotency_key
        assert idemp_key is not None
        
        assert initiate(idempotency_key=idemp_key, billing=processed.billing) == processed

        # For pending payment on billing
        pending = payment_factory(statuses=[PS.PENDING], billing=billings[2])[0]
        assert initiate(billing=billings[2], idempotency_key="XYZ3") == pending
