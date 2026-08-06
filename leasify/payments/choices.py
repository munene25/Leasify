from django.db.models import TextChoices

class PaymentStatus(TextChoices):
    """PENDING, SUCCESS or FAILED STATUS"""
    PENDING = "pending", "Payment Pending"
    SUCCESS = "success", "Payment Success"
    FAILED = "failed", "Payment Failed"

class PaymentMode(TextChoices):
    """MPESA, CASH, BANK"""
    MPESA = "MPESA"
    CASH = "CASH"
    BANK = "BANK"