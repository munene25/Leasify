from typing import TYPE_CHECKING
from enum import StrEnum
from decimal import Decimal
from django.db import models
from common.models import BaseModel
from common.period import DateRange, today
from datetime import date, timedelta
from tenancy.models import Tenancy

MAX_BILLING_PERIOD: int = 4

if TYPE_CHECKING:
    from payments.models import Payment
    from django.db.models import QuerySet


class BillingPeriod(BaseModel):
    """
    This describes the billing period for a tenant
    All billing periods are expected to be quantized 
    """
    class Meta:
        ordering = ("-start_date",)
        indexes = [
            models.Index(fields=("tenancy", "start_date", "end_date")),
        ]

    class BillingStatus(StrEnum):
        CLEARED = "cleared"
        PENDING = "pending"

    tenancy = models.ForeignKey(Tenancy, on_delete=models.PROTECT, null=False, blank=False, related_name="billings")
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)
    rent_snapshot = models.DecimalField(decimal_places=2, max_digits=10)

    payments: "QuerySet[Payment]"

    @property
    def is_current(self) -> bool:
        """Check if the tenancy is current"""
        return self.start_date <= today() <= self.end_date

    @property
    def total_due(self) -> Decimal:
        return (self.rent_snapshot * self.duration_months).quantize(Decimal("0.01"))

    @property
    def next_start(self) -> date:
        """All billing periods should be consecutive and ordered"""
        return self.end_date + timedelta(days=1)

    @property
    def total_paid(self) -> Decimal:
        """Calculate the total amount of money due from the tenant based on their duration of stay"""
        from payments.models import Payment

        totals = self.payments.aggregate(
            debits=models.Sum("amount", filter=models.Q(transaction_type=Payment.TransactionChoices.DEBIT)),
            credits=models.Sum("amount", filter=models.Q(transaction_type=Payment.TransactionChoices.CREDIT)),
        )
        return (totals["debits"] or Decimal(0)) - (totals["credits"] or Decimal(0))

    @property
    def is_cleared(self) -> BillingStatus:
        if self.total_due > self.total_paid:
            return self.BillingStatus.PENDING
        return self.BillingStatus.CLEARED

    @property
    def duration_months(self) -> int:
        """
        Calculate the duration of the tenancy in months
        This calculation relies on the fact that all tenancies begin on the first day of the month and last day of the month.
        Enforced at the service layer when creating tenancies.
        """

        return DateRange(self.start_date, self.end_date).duration_months
