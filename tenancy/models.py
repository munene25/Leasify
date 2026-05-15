from typing import TYPE_CHECKING
from datetime import timedelta
from django.db import models
from django.utils import timezone
from users.models import User
from common.models import BaseModel
from apartments.models import Apartment

if TYPE_CHECKING:
    from payments.models import Payment
    from django.db.models import QuerySet



GRACE_PERIOD = timedelta(weeks=2)
DEFAULT_RESERVATION_DURATION = timedelta(days=2)
MOVING_WINDOW = timedelta(weeks=2)
MAX_RESERVATIONS_PER_USER = 2

get_default_reservation_expiry_date = lambda: timezone.now().date() + DEFAULT_RESERVATION_DURATION

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

    class TenancyStatus(models.TextChoices):
        PENDING = "pending", "Tenant has made a reservation but has not paid yet"
        ACTIVE = "active", "Tenant has paid and the tenancy is active"
        EXPIRED = "expired", "Reservation has expired without payment"
        TERMINATED = "terminated", "Tenancy has been explicitly terminated"


    user = models.ForeignKey(User, on_delete=models.PROTECT, null=False, blank=False)
    apartment = models.ForeignKey(Apartment, on_delete=models.PROTECT, null=False, blank=False)
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)
    total_due = models.DecimalField(decimal_places=2, max_digits=10)
    total_paid = models.DecimalField(decimal_places=2, max_digits=10)
    status = models.CharField(max_length=20, choices=TenancyStatus.choices, default=TenancyStatus.PENDING)
    reservation_expiration = models.DateField(null=False, blank=False, default=get_default_reservation_expiry_date)

    user_id: int
    apartment_id: int
    payment_records: "QuerySet[Payment]"

    def __str__(self) -> str:
        return f"user:{self.user_id} - tenancy:{self.pk}"

    @property
    def active(self) -> bool:
        """Check if the tenancy is currently active"""
        now = timezone.now().date()
        return self.start_date <= now <= self.end_date

    @property
    def duration_months(self,) -> int:
        """
        Calculate the duration of the tenancy in months
        This calculation relies on the fact that all tenancies begin on the first day of the month and last day of the month.
        Enforced at the service layer when creating tenancies.
        """

        from dateutil.relativedelta import relativedelta

        return relativedelta(self.end_date, self.start_date).months + 1
        
    @property
    def has_ended(self) -> bool:
        """Check if the tenancy has ended"""
        return self.end_date < timezone.now().date()
