from django.db import models
from enum import StrEnum
from apartments.models import Apartment
from users.models import User
from common.models import BaseModel
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

GRACE_PERIOD = timedelta(weeks=2)


class TenantPaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PENDING = "pending"
    CLEARED = "cleared"
    OVERPAID = "overpaid"


class Tenancy(BaseModel):
    """
    Lease-based tenancy model. Each tenancy represents a user's lease for an apartment
    within a specific time period. Tenancies are no longer tied to semesters.

    We track who rented when the tenancy existed, where the tenant resided and at what agreed amount.
    If rent is increased for an apartment, historical tenancies which relied on the apartment.rent
    fail to portray the correct payment status. This is why we store agreed rent on the tenancy.
    """

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["apartment", "start_date", "end_date"]),
        ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, null=False, blank=False)
    apartment = models.ForeignKey(Apartment, on_delete=models.PROTECT, null=False, blank=False)
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)
    lease_rent = models.DecimalField(decimal_places=2, max_digits=10)
    total_paid = models.DecimalField(decimal_places=2, max_digits=10)
    user_id: int
    apartment_id: int

    def __str__(self) -> str:
        return f"user:{self.user_id} - tenancy:{self.pk}"

    @property
    def balance(self) -> Decimal:
        """The amount of money owed by the tenant"""
        return self.lease_rent - self.total_paid

    @property
    def payment_status(self) -> TenantPaymentStatus:
        if self.total_paid <= 0:
            return TenantPaymentStatus.UNPAID
        elif self.total_paid < self.lease_rent:
            return TenantPaymentStatus.PENDING
        elif self.total_paid == self.lease_rent:
            return TenantPaymentStatus.CLEARED
        return TenantPaymentStatus.OVERPAID

    @property
    def active(self) -> bool:
        """Check if the tenancy is currently active"""
        now = timezone.now().date()
        return self.start_date <= now <= self.end_date

    @property
    def has_ended(self) -> bool:
        """Check if the tenancy has ended"""
        return self.end_date < timezone.now().date()

    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days
    
    def duration_months(self) -> int:
        return self.duration_days() // 30  # Approximate month as 30 days
    
    def effective_rent(self) -> Decimal:
        """calculate the total rent for the tenancy period"""
        return (self.lease_rent * self.duration_months()).quantize(Decimal("0.01"))
