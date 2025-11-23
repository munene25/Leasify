from django.db import models
from django.core.exceptions import ValidationError
from semesters.models import Semester


class Apartment(models.Model):
    """
    This is the base apartment with the block it belongs to, the unit number within the block
    Rent is more closely tied to semester and is set on the Semester model
    """

    class ApartmentChoices(models.TextChoices):
        NEW = "NEW", "New Block"
        OLD = "OLD", "OLD Block"

    block = models.CharField(max_length=10, choices=ApartmentChoices.choices)
    unit_number = models.PositiveSmallIntegerField()
    rent = models.DecimalField(decimal_places=2, max_digits=10, blank=False, null=False)
    available = models.BooleanField(default=True)

    class Meta:
        unique_together = ("block", "unit_number")

    def __str__(self) -> str:
        return f"Block: {self.block} - Unit: {self.unit_number}"

    @property
    def occupied(self):
        return self.tenancy_set.filter(semester=Semester.current_semester()).exists()

    @property
    def current_tenant(self):
        curr = self.tenancy_set.select_related("user").filter(semester=Semester.current_semester()).first()
        return curr if curr else None

    @property
    def apartment_name(self):
        """
        Representation of the apartment block and number.
        """
        return f"{self.block}-{self.unit_number:02}"