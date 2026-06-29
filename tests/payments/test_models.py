import pytest
from django.db import IntegrityError
from tests.types import Factory
from payments.models import Payment
from payments.choices import PaymentStatus as PS, PaymentMode as PM
from billing.models import BillingPeriod as BP
from users.models import User


class TestPaymentModel:
    """Test Payment model creation and validation."""

    def test_payment_creation(self, billing_factory: Factory[BP], phone_no):
        """The default non nullable fields for a payment creation"""
        billing = billing_factory(1)[0]

        Payment.objects.create(
            billing=billing,
            amount=billing.total_due,
            status=PS.SUCCESS,
            payment_mode=PM.MPESA,
            phone_number=phone_no(),
            timestamp="20202022",
            receipt_no="Reciept2020-22",
            idempotency_key="202020",
        )

        assert len(Payment.objects.all()) == 1

    def test_payment_creation_manual(self, billing_factory: Factory[BP], user_factory: Factory[User]):
        """Test that a payment can be created manually without MPESA-specific fields.

        Manual payments (CASH/BANK) don't require checkout_id or phone_number but need recorded_by.
        Uses existing fixtures from conftest.py (user and tenant_user).
        """
        # Create manual payment with recorded_by but no checkout_id/phone_number (manual mode)
        user = user_factory(1)[0]
        billing = billing_factory(1)[0]

        p = Payment.objects.create(
            billing=billing,
            amount=billing.total_due,  # type: ignore
            status=PS.SUCCESS,
            payment_mode=PM.CASH,
            recorded_by=user,  # Required for manual payments
        )

        assert len(Payment.objects.all()) == 1

    def test_duplicate_checkout_id_raises(self, billing_factory: Factory):
        """Test that creating a payment with duplicate checkout_id raises IntegrityError."""
        billing = billing_factory(1)[0]
        p = Payment.objects.create(
            billing=billing,
            amount=billing.total_due,
            status=PS.SUCCESS,
            payment_mode=PM.CASH,
            checkout_id="uniquecheckoutid",
        )
        with pytest.raises(IntegrityError):
            Payment.objects.create(
                billing=billing,
                amount=billing.total_due,
                status=PS.SUCCESS,
                payment_mode=PM.MPESA,
                checkout_id=p.checkout_id,
            )

    def test_duplicate_idempotency_key_raises(self, billing_factory: Factory):
        """Test that creating a payment with duplicate idempotency_key raises IntegrityError."""
        billing = billing_factory(1)[0]
        p = Payment.objects.create(
            billing=billing,
            amount=billing.total_due,
            status=PS.SUCCESS,
            payment_mode=PM.CASH,
            idempotency_key="unique_idemp_key",
        )
        # Duplicate IDEMPOTENCY_KEY should fail
        with pytest.raises(IntegrityError):
            Payment.objects.create(
                billing=billing,
                amount=billing.total_due,
                status=PS.SUCCESS,
                payment_mode=PM.MPESA,
                idempotency_key=p.idempotency_key,
            )
