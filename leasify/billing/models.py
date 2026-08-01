from typing import TYPE_CHECKING
from django.db import models
from rest_framework.exceptions import ValidationError
from leasify.common.models import BaseModel
from leasify.common.period import DateRange, today
from datetime import date, timedelta
from leasify.tenancy.models import Tenancy
from leasify.billing.choices import BillingStatus

MAX_BILLING_PERIOD: int = 4

if TYPE_CHECKING:
    from leasify.payments.models import Payment
    from django.db.models import QuerySet


class BillingPeriod(BaseModel):
    """
    This describes the billing period for a tenant
    All billing periods are expected to be quantized 
    """
    class Meta:
        ordering = ("-start_date", "-created_at")
        indexes = [
            models.Index(fields=("tenancy", "start_date", "end_date")),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenancy"],
                condition=models.Q(status=BillingStatus.UNPAID),
                name="unique_unpaid_billing_per_tenancy",
                violation_error_message="An 'UNPAID' billing period already exists for this tenant",
            )
        ]
        permissions = [
            ("complete_billingperiod", "Can manually set the billing period to PAID"),
        ]


    tenancy = models.ForeignKey(Tenancy, on_delete=models.PROTECT, null=False, blank=False, related_name="billings")
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)
    status = models.CharField(null=False, blank=False, default=BillingStatus.UNPAID)
    total_due = models.DecimalField(decimal_places=2, max_digits=10, null=False, blank=False)

    payments: "QuerySet[Payment]"
    tenancy_id: int

    @property
    def is_current(self) -> bool:
        """Check if the tenancy is current"""
        return self.start_date <= today() <= self.end_date


    @property
    def next_start(self) -> date:
        """All billing periods should be consecutive and ordered"""
        if not self.status == BillingStatus.PAID:
            raise ValidationError("Next start can only be computed from paid billing periods")

        return self.end_date + timedelta(days=1)

    @property
    def duration_months(self) -> int:
        """
        Calculate the duration of the tenancy in months
        This calculation relies on the fact that all tenancies begin on the first day of the month and last day of the month.
        Enforced at the service layer when creating tenancies.
        """

        return DateRange(self.start_date, self.end_date).duration_months

    def __str__(self) -> str:
        """Outputs it in the form of a string e.g. '[JUN-2025]-[JUL-2025]' """
        start = self.start_date.strftime('%b-%Y').upper()
        end = self.end_date.strftime('%b-%Y').upper()
        return f"[{start}][{end}]"
    
    @property
    def name(self) -> str:
        """Outputs it in the form of a string e.g. 'Jan 2025' or 'Feb 2026 to Mar 2026' """
        start = self.start_date.strftime("%b %Y")
        end = self.end_date.strftime("%b %Y")
        if start == end:
            return start
        return f"{start} to {end}"