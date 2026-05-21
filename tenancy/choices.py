""""

This seperation is intended to avoid model not ready
Also from time to time I end up dealing with circular imports.

"""
from django.db.models import TextChoices


class Status(TextChoices):
    ACTIVE = "active", "Tenant has paid and the tenancy is active"
    RESERVED = "pending", "Tenant has made a reservation but has not paid yet"
    DEFAULTING = "defaulting", "Active tenant has not yet paid"
    TERMINATED = "terminated", "Tenancy has been expired"

class TerminationReason(TextChoices):
    MANAGERIAL = "managerial", "Managerial decision to terminate"
    EXPIRED = "expired", "Reservation expired"
    VOLUNTARY = "voluntary", "Voluntary termination"
    NONPAYMENT = "non_payment", "Tenant failed to pay"


active_reserved_defaulting = [Status.ACTIVE, Status.RESERVED, Status.DEFAULTING]
reserved_or_terminated = [Status.RESERVED, Status.TERMINATED]
