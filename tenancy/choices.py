""" "

This seperation is intended to avoid model not ready
Also from time to time I end up dealing with circular imports.

"""

from django.db.models import TextChoices


class TenancyStatus(TextChoices):
    "ACTIVE, RESERVED, DEFAULTING, OR TERMINATED"

    ACTIVE = "active", "Tenant has paid and the tenancy is active"
    RESERVED = "reserved", "Tenant has made a reservation but has not paid yet"
    DEFAULTING = "defaulting", "Active tenant has not yet paid"
    TERMINATED = "terminated", "Tenancy has been expired"


class TerminationReason(TextChoices):
    """MANAGERIAL, EXPIRED, VOLUNTARY OR NONPAYMENT"""

    MANAGERIAL = "managerial", "Managerial decision to terminate"
    EXPIRED = "expired", "Reservation expired"
    VOLUNTARY = "voluntary", "Voluntary termination"
    NONPAYMENT = "non_payment", "Tenant failed to pay"


ACTIVE_RESERVED_OR_DEFAULTING = [TenancyStatus.ACTIVE, TenancyStatus.RESERVED, TenancyStatus.DEFAULTING]
RESERVED_OR_TERMINATED = [TenancyStatus.RESERVED, TenancyStatus.TERMINATED]
