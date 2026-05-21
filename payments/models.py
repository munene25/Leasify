from django.db import models
from billing.models import BillingPeriod
from decimal import Decimal
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

    billing = models.ForeignKey(BillingPeriod, null=False, blank=False, on_delete=models.SET_NULL, related_name="payments")
    ref_no = models.UUIDField(primary_key=True, max_length=20, unique=True, null=False, blank=False, editable=False)
    initiator = models.CharField(null=False, blank=False, choices=PaymentInitiator)
    phone_number = PhoneNumberModelField(null=False, blank=False, editable=False)
    amount = models.DecimalField(decimal_places=2, max_digits=10, editable=False, blank=False, null=False)
    transaction_type = models.CharField(null=False,blank=False, max_length=10, editable=False, choices=TransactionType.choices)
   
    status = models.CharField(null=False, blank=False, choices=PaymentStatus, default=PaymentStatus.PENDING)
    payee = models.CharField(max_length=30, null=True, blank=True)

    billing_id: int

    def __str__(self):
        return f"Ref: {self.ref_no} Amt: {self.amount} Type: ({self.transaction_type})"

