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
    total_paid = models.DecimalField(decimal_places=2, max_digits=10)
    user_id: int
    semester_id: int
    apartment_id: int


    def __str__(self) -> str:
        return f"user:{self.user_id} - tenancy:{self.pk}"

    @property
    def balance(self) -> Decimal:
        """The amount of money owed by the tenant"""
        return self.apartment.rent - self.total_paid

    @property
    def payment_status(self) -> TenantPaymentStatus:
        # options are unpaid, pending, cleared
        if self.total_paid <= 0:
            return TenantPaymentStatus.UNPAID
        elif self.total_paid < self.apartment.rent:
            return TenantPaymentStatus.PENDING
        elif self.total_paid == self.apartment.rent:
            return TenantPaymentStatus.CLEARED
        return TenantPaymentStatus.OVERPAID