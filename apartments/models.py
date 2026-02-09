from typing import Collection
from django.db import models
from django.db.models.query import QuerySet
from semesters.selectors import semester_current
from mixins.model_full_clean import ModelExceptionMixin


class Apartment(
    ModelExceptionMixin,
    models.Model,
):
    """
    Apartment Model.
    Fields block and unit number must be unique for every entry.
    Rentable flag describes if the apartment is viewable for other users and tenants looking to book.
    """

    class ApartmentChoices(models.TextChoices):
        NEW = "NEW", "New Block"
        OLD = "OLD", "OLD Block"

    block = models.CharField(max_length=10, choices=ApartmentChoices.choices)
    unit_number = models.PositiveSmallIntegerField()
    rent = models.DecimalField(decimal_places=2, max_digits=10, blank=False, null=False)
    rentable = models.BooleanField(
        default=True, help_text="Viewable and available to rent"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("block", "unit_number")

    def __str__(self) -> str:
        return f"Block: {self.block} - Unit: {self.unit_number}"

    @property
    def apartment_name(self) -> str:
        """
        Representation of the apartment block and number.
        """
        return f"{self.block}-{self.unit_number:02}"

    # --- Might cause N + 1 if not prefetched ----
    # --- Consider moving to a dedicated selector with annotations
    @property
    def current_tenant(self) -> QuerySet:
        tset = getattr(self, "tenancy_set")
        curr = tset.select_related("user").filter(semester=semester_current()).first()
        return curr

    @property
    def occupied(self) -> bool:
        return True if self.current_tenant else False
