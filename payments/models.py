from django.db import models
from billing.models import BillingPeriod
import uuid
from common.models import BaseModel
from common.fields import PhoneNumberModelField
from payments.choices import PaymentStatus, PaymentInitiator

class Payment(BaseModel):
    """
    Payment will have 2 states, once initiated and then confirmed
    On confirmation, status changes to either FAILED or SUCCESS.
    """
    class Meta:
        indexes = [
            models.Index(fields=["status"])
        ]


    billing = models.ForeignKey(BillingPeriod, null=False, blank=False, on_delete=models.PROTECT, related_name="payments")
    receipt_no = models.CharField(null=True, blank=True)
    initiator = models.CharField(null=False, blank=False, choices=PaymentInitiator)
    phone_number = PhoneNumberModelField(null=False, blank=False, editable=False)
    checkout_id = models.CharField(db_index=True, unique=True, null=False, blank=False)
    amount = models.DecimalField(decimal_places=2, max_digits=10, editable=False, blank=False, null=False)
    status = models.CharField(null=False, blank=False, choices=PaymentStatus, default=PaymentStatus.PENDING)
    payee = models.CharField(max_length=30, null=True, blank=True)

    billing_id: int

    @property
    def ref_no(self) -> str:
        return f"{self.initiator}-{str(self.checkout_id).upper()}"

