from django.db.models import TextChoices

class PaymentStatus(TextChoices):
    """PENDING, SUCCESS or FAILED STATUS"""
    PENDING = "pending", "Payment has been initiated but not confirmed"
    SUCCESS = "success", "Payment has been confirmed and funds have transferred"
    FAILED = "failed", "Payment could not be completed"

class PaymentInitiator(TextChoices):
    """TENANT OR ADMIN INITIATED PAYMENT"""
    TENANT = "TPY", "System initiated"
    ADMIN = "APY", "System initiated"