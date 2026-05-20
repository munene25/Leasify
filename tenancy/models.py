from datetime import timedelta
from django.db import models
from common.period import today
from users.models import User
from common.models import BaseModel
from apartments.models import Apartment

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
    """

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # only one active/pending tenancy per apartment at a time
            models.UniqueConstraint(
                fields=["apartment"],
                condition=models.Q(status__in=["active", "pending"]),
                name="unique_active_pending_per_apartment"
            ),
            # only one active/pending tenancy per user at a time
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status__in=["active", "pending"]),
                name="unique_active_pending_per_user"
            ),
        ]
        permissions = (
            ("tenancy_extend_lease", "Allow tenancy lease time to be extended"),
            ("tenancy_extend_reservation_expiration", "Allow pending tenants to extend their stay"),
        )

    class Status(models.TextChoices):
        PENDING = "pending", "Tenant has made a reservation but has not paid yet"
        ACTIVE = "active", "Tenant has paid and the tenancy is active"
        TERMINATED = "terminated", "Tenancy has been expired"

    user = models.ForeignKey(User, on_delete=models.PROTECT, null=False, blank=False)
    apartment = models.ForeignKey(Apartment, on_delete=models.PROTECT, null=False, blank=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reservation_expriry = models.DateField(blank=False, null=False, default=default_expiry)

    user_id: int
    apartment_id: int
    
    def __str__(self) -> str:
        return f"user:{self.user_id} - tenancy:{self.pk}"

    

