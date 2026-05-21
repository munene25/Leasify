from django.db.models import TextChoices

class TransactionType(TextChoices):
    DEBIT = "debit", "Incoming Payments"
    CREDIT = "credit", "Outgoing Payments"

class PaymentStatus(TextChoices):
    PENDING = "pending", "Payment has been initiated but not confirmed"
    CONFIRMED = "confirmed", "Payment has been confirmed"
    FAILED = "failed", "Payment could not be completed"

class PaymentInitiator(TextChoices):
    SYSTEM = "SGT", "System initiated"
    TENANT = "TPY", "System initiated"
    ADMIN = "APY", "System initiated"