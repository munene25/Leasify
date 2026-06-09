from typing import TYPE_CHECKING
from datetime import timedelta
from django.db import models
from common.period import today
from users.models import User
from common.models import BaseModel
from apartments.models import Apartment
from tenancy.choices import TenancyStatus, TerminationReason
from functools import cached_property


if TYPE_CHECKING:
    from datetime import date
    from billing.models import BillingPeriod

GRACE_PERIOD = timedelta(weeks=1)
DEFAULT_RESERVATION_DURATION = timedelta(days=2)
MAX_RESERVATIONS_PER_USER = 2


def default_expiry():
    return today() + DEFAULT_RESERVATION_DURATION


class Tenancy(BaseModel):
    """
    Lease-based tenancy model. Each tenancy represents a user's lease for an apartment
    within a specific time period. Tenancies are no longer tied to semesters.

    We track who rented when the tenancy existed, where the tenant resided and at what agreed rent.
    If rent is increased for an apartment, historical tenancies which relied on the apartment.rent
    fail to portray the correct payment status. This is why we store agreed rent on the tenancy.
    ? Maybe add expired status for expired booking attempts over terminated
    ? Maybe add start date to know the time the tenant has been around
    """

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # only one active/reserved/defaulting tenancy per apartment at a time
            models.UniqueConstraint(
                fields=["apartment"],
                condition=models.Q(status__in=["active", "reserved", "defaulting"]),
                name="unique_active_pending_per_apartment",
                violation_error_message="Apartment already associated with a tenant",
            ),
            # only one active/reserved/defaulting tenancy per user at a time
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status__in=["active", "reserved", "defaulting"]),
                name="unique_active_pending_per_user",
                violation_error_message="User already has a tenancy",
            ),
        ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, null=False, blank=False)
    apartment = models.ForeignKey(Apartment, on_delete=models.PROTECT, null=False, blank=False)
    status = models.CharField(max_length=20, choices=TenancyStatus.choices, default=TenancyStatus.RESERVED)
    date_joined = models.DateField(blank=False, null=False)
    reservation_expiry = models.DateField(blank=False, null=False, default=default_expiry)
    termination_reason = models.CharField(choices=TerminationReason.choices, blank=True, null=True)
    termination_date = models.DateField(blank=True, null=True)

    user_id: int
    apartment_id: int
    billings: models.QuerySet["BillingPeriod"]

    def __str__(self) -> str:
        return f"user:{self.user_id} - tenancy:{self.pk}"

    @property
    def is_continuing(self) -> bool:
        """
        This is very different from whether they can create a billing period.
        Better not to bleed Billing period domain logic into tenancy.
        """

        return self.status in [TenancyStatus.DEFAULTING, TenancyStatus.ACTIVE]

    @property
    def has_pending_bills(self) -> bool:
        from billing.choices import BillingStatus

        return self.billings.filter(status=BillingStatus.UNPAID).exists()

    @property
    def last_paid_billing(self) -> "BillingPeriod":
        """Use the selector here to avoid checking for not found"""
        from billing.selectors import billing_last_paid_for

        return billing_last_paid_for(self.pk)
    
    @cached_property
    def paid_up_to(self) -> "date":
        """
        This might be important to get view they are paid up to what date.
        """
        return self.last_paid_billing.end_date