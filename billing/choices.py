from django.db.models import TextChoices


class BillingStatus(TextChoices):
    PAID = "paid", "Full payment has been made"
    UNPAID = "unpaid", "No payment has been made"
    CANCELLED = "cancelled", "Canceled by user, non deletion allows audit trails"
