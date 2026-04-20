from __future__ import annotations 
from django.db import models
from common.models import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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

    block = models.CharField(max_length=10, choices=ApartmentChoices.choices, blank=False, null=False)
    unit_number = models.PositiveSmallIntegerField(blank=False, null=False)
    rent = models.DecimalField(decimal_places=2, max_digits=10, blank=False, null=False)
    rentable = models.BooleanField(
        default=True, blank=False, help_text="Viewable and available to rent"
    )
    tenancy_set: models.QuerySet[Tenancy]


    def __str__(self) -> str:
        return f"{self.block}-{self.unit_number:02}"

    @property
    def apartment_name(self) -> str:
        """
        Representation of the apartment block and number.
        """
        return str(self)

    
    @property
    def current_tenant(self) -> Tenancy | None:
        """
        ! REQUIRES CURRENT_TENANT_PREFETCH
        Return the current tenant if they exist.
        """
        return self.tenancy_set.first()
    
    @property
    def occupied(self) -> bool:
        """
        ! REQUIRES CURRENT_TENANT_PREFETCH
        Whether or not the apartment is currently occupied.
        """
        return self.tenancy_set.exists()
