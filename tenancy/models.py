from django.db import models
from apartments.models import Apartment
from users.models import User
from semesters.models import Semester
from mixins.model_full_clean import ModelExceptionMixin


class Tenancy(ModelExceptionMixin, models.Model):
    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "semester"], name="unique_user_per_semester"
            ),
            models.UniqueConstraint(
                fields=["apartment", "semester"],
                name="unique_apartment_per_semester",
            ),
        ]
    
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=False, blank=False)
    apartment = models.ForeignKey(
        Apartment, on_delete=models.PROTECT, null=False, blank=False
    )
    semester = models.ForeignKey(
        Semester, on_delete=models.PROTECT, null=False, blank=False
    )
    total_paid = models.DecimalField(
        decimal_places=2,
        max_digits=10,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    
    def __str__(self) -> str:
        return f"[{self.pk}] User: {getattr(self, "user_id")} Apt: {getattr(self, "apartment_id")}"

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
        return self.user.account.phone_number #type: ignore

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
