from django.db import models
from enum import StrEnum
from apartments.models import Apartment
from users.models import User
from semesters.models import Semester
from common.models import BaseModel
from decimal import Decimal


class TenantPaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PENDING = "pending"
    CLEARED = "cleared"
    OVERPAID = "overpaid"

class Tenancy(BaseModel):
    """
    We need to track who rented when the tenancy existed, where the tenant resided and at what agreed amout
    If rent is increased for an apartment, historical tenancies which relied on the apartment.rent
    fail to portray the correct payment status.

    This is why we need agreed rent on the tenancy on creating the rent
    """
    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "semester"], 
                name="unique_user_per_semester"
            ),
            models.UniqueConstraint(
                fields=["apartment", "semester"],
                name="unique_apartment_per_semester",
            ),
        ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, null=False, blank=False)
    apartment = models.ForeignKey(Apartment, on_delete=models.PROTECT, null=False, blank=False)
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, null=False, blank=False)
    lease_rent = models.DecimalField(decimal_places=2, max_digits=10)
    total_paid = models.DecimalField(decimal_places=2, max_digits=10)
    user_id: int
    semester_id: int
    apartment_id: int


    def __str__(self) -> str:
        return f"user:{self.user_id} - tenancy:{self.pk}"

    @property
    def balance(self) -> Decimal:
        """The amount of money owed by the tenant"""
        return self.lease_rent - self.total_paid

    @property
    def payment_status(self) -> TenantPaymentStatus:
        # options are unpaid, pending, cleared
        if self.total_paid <= 0:
            return TenantPaymentStatus.UNPAID
        elif self.total_paid < self.lease_rent:
            return TenantPaymentStatus.PENDING
        elif self.total_paid == self.lease_rent:
            return TenantPaymentStatus.CLEARED
        return TenantPaymentStatus.OVERPAID