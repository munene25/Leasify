from django.db import models
from tenancy.models import Tenancy
from decimal import Decimal
from common.models import BaseModel
from common.fields import PhoneNumberModelField


class Payment(BaseModel):
    class TransactionChoices(models.TextChoices):
        DEBIT = "debit", "Incoming Payments"
        CREDIT = "credit", "Outgoing Payments"

    ref_no = models.CharField(max_length=20, unique=True, editable=False)
    amount = models.DecimalField(
        decimal_places=2, max_digits=10, blank=False, null=False
    )
    transaction_type = models.CharField(
        null=False, max_length=10, choices=TransactionChoices.choices
    )
    tenancy = models.ForeignKey(Tenancy, null=True, on_delete=models.SET_NULL)
    phone_number = PhoneNumberModelField(null=False, blank=False)
    payee = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"Ref: {self.ref_no} Amt: {self.amount} Type: ({self.transaction_type})"

    @classmethod
    def get_total_payments_received(cls, semester):
        dr = models.Q(
            transaction_type=cls.TransactionChoices.DEBIT, tenancy__semester=semester
        )
        cr = models.Q(
            transaction_type=cls.TransactionChoices.CREDIT, tenancy__semester=semester
        )
        received = cls.objects.select_related("tenancy").aggregate(
            debit=models.Sum("amount", filter=dr),
            credit=models.Sum("amount", filter=cr),
        )
        debit = received["debit"] or Decimal("0")
        credit = received["credit"] or Decimal("0")
        return debit - credit

    @classmethod
    def get_payment_history_for_user(cls, tenancy):
        """
        Get entire payment history associated with a user across semesters.
        """
        return cls.objects.select_related("tenancy").filter(tenancy__user=tenancy.user)

    @classmethod
    def get_payment_history_for_tenancy(cls, tenancy):
        """
        Get payment history associated with a tenant for a certain semester.
        """
        return cls.objects.filter(tenancy=tenancy)
