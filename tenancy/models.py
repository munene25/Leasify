from decimal import Decimal
from django.db import models
from apartments.models import Apartment
from users.models import User
from semesters.models import Semester
from django.db import transaction


class Tenancy(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    apartment = models.ForeignKey(
        Apartment, on_delete=models.PROTECT, null=False, blank=False
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.PROTECT, null=False, blank=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    total_paid = models.DecimalField(
        decimal_places=2, max_digits=10, default=Decimal(0)
    )


    class Meta:
        sorting = ["-created_at"]
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

    def __str__(self) -> str:
        return f"Pk: {self.user.pk} Apt: {self.apartment}"

    @transaction.atomic
    def update_ledger_from_payment(self, payment):
        if payment.transaction_type == "debit":
            self.total_paid += payment.amount
        else:
            self.total_paid -= payment.amount
        self.save()

    @classmethod
    def get_semester_tenants(cls, semester):
        return cls.objects.select_related("user", "apartment").filter(
            semester=semester, is_active=True
        )

    @classmethod
    def get_total_payments_received(cls, semester):
        total = cls.objects.filter(semester=semester).aggregate(
            total=models.Sum("total_paid")
        )
        return total.get("total", Decimal("0.00"))

    @classmethod
    def get_uncleared_tenant_list(cls, semester):
        """
        Get a list of current tenants with uncleared balances for that semester
        """
        qs_filter = models.Q(ledger__total_paid__lt=models.F("rent")) | models.Q(
            ledger__isnull=True
        )
        return cls.get_semester_tenants(semester).filter(qs_filter)

    @property
    def balance(self):
        """
        On each tenancy instance get the balance based computed form joined apartment rent , fetch balance.
        """
        return self.apartment.rent - self.total_paid


    @property
    def tenant_name(self):
        return self.user.get_full_name()

    @property
    def apartment_name(self):
        return self.apartment.apartment_name

    @property
    def phone_number(self):
        return self.user.phone_number

    @property
    def payment_status(self):
        rent = self.apartment.rent
        balance = rent - self.total_paid
        if balance < 0:
            payment_status = "owing"
        elif balance == 0:
            payment_status = "cleared"
        elif rent > balance > 0:
            payment_status = "pending"
        elif balance == rent:
            payment_status = "unpaid"
        else:
            payment_status = "unpaid with arrears"

        return payment_status
