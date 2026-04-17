from django.db import models
from django.db.models.query import QuerySet
from semesters.selectors import semester_current
from common.models import BaseModel
from common.helpers import raise_not_found
from tenancy.models import Tenancy
class Apartment(BaseModel):
    """
    Apartment Model.
    Fields block and unit number must be unique for every entry.
    Rentable flag describes if the apartment is viewable for other users and tenants looking to book.
    """

    class Meta:
        unique_together = ("block", "unit_number")
        permissions = (
            ("view_overview", "Can view the apartments overview status for the semester"),
        )
    
    class ApartmentChoices(models.TextChoices):
        NEW = "NEW", "New Block"
        OLD = "OLD", "OLD Block"

    block = models.CharField(max_length=10, choices=ApartmentChoices.choices, blank=False, null=False,)
    unit_number = models.PositiveSmallIntegerField(blank=False, null=False)
    rent = models.DecimalField(decimal_places=2, max_digits=10, blank=False, null=False)
    rentable = models.BooleanField(
        default=True, blank=False, help_text="Viewable and available to rent"
    )
    tenancy_set: models.QuerySet[Tenancy]


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
    def current_tenant(self) -> Tenancy | None:
        """Return the current tenant if they exist"""
        current_tenant = self.tenancy_set.select_related("user").filter(semester_id=semester_current().pk).first()
        return current_tenant
    
    @property
    def occupied(self) -> bool:
        return True if self.current_tenant else False
