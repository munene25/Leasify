from django.db import models
from billing.models import BillingPeriod
import uuid
from common.models import BaseModel
from common.fields import PhoneNumberModelField
from payments.choices import PaymentStatus, TransactionType, PaymentInitiator

class Payment(BaseModel):
    """
    Payment will have 2 states, once initiated and then confirmed
    At inititaion, phone, ref, amount, transaction_type, billing status and intiator are defined
    At confirmation, the payee is filled out.
    ? Maybe get the mpesa confirmation code upon
    """
    class Meta:
        indexes = [
            models.Index(fields=["status"])
        ]


    billing = models.ForeignKey(BillingPeriod, null=False, blank=False, on_delete=models.PROTECT, related_name="payments")
    id = models.UUIDField(primary_key=True, db_index=True, default=uuid.uuid4, editable=False)
    initiator = models.CharField(null=False, blank=False, choices=PaymentInitiator)
    phone_number = PhoneNumberModelField(null=False, blank=False, editable=False)
    amount = models.DecimalField(decimal_places=2, max_digits=10, editable=False, blank=False, null=False)
    transaction_type = models.CharField(null=False,blank=False, max_length=10, editable=False, choices=TransactionType.choices)
   
    status = models.CharField(null=False, blank=False, choices=PaymentStatus, default=PaymentStatus.PENDING)
    payee = models.CharField(max_length=30, null=True, blank=True)

    billing_id: int

    @property
    def ref_no(self) -> str:
        return f"{self.initiator}-{str(self.pk).upper()}"

