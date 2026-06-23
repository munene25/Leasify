from django.db import models
from common.models import BaseModel
from common.fields import PhoneNumberModelField
from billing.models import BillingPeriod
from payments.choices import PaymentStatus, PaymentMode
from users.models import User


class Payment(BaseModel):
    """
    Two creation paths:
    - STK push (MPESA): checkout_id and phone_number are populated, recorded_by is null
    - Manual (CASH/BANK): recorded_by is populated, checkout_id and phone_number are null

    Payer identity is resolved via billing -> tenancy -> tenant.
    receipt_no is populated on MPESA callback confirmation or provided manually.
    """

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["checkout_id"]),
            models.Index(fields=["receipt_no"]),
            models.Index(fields=["idemp_key"]),
        ]
        permissions = [
            ("add_payment_manually", "Can manually create a payment"),
        ]

    # Required
    billing = models.ForeignKey(
        BillingPeriod, null=False, blank=False, on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.DecimalField(decimal_places=2, max_digits=10, blank=False, null=False)
    status = models.CharField(null=False, blank=False, choices=PaymentStatus, default=PaymentStatus.PENDING)
    payment_mode = models.CharField(null=False, blank=False, choices=PaymentMode)

    # MPESA only
    phone_number = PhoneNumberModelField(null=True, blank=True)
    checkout_id = models.CharField(unique=True, null=True, blank=True)
    receipt_no = models.CharField(null=True, blank=True)
    timestamp = models.CharField(null=True, blank=True)
    idemp_key = models.CharField(null=True, blank=True, unique=True)

    # Manual only for cash/bank payments
    recorded_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.PROTECT, related_name="recorded_payments"
    )

    billing_id: int

    @property
    def ref_no(self) -> str:
        return f"{self.payment_mode}-{str(self.pk).upper()}"
