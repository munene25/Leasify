from __future__ import annotations
from typing import TYPE_CHECKING
from django.db import models
from common.models import BaseModel
from tenancy.choices import active_reserved_defaulting

if TYPE_CHECKING:
    from tenancy.models import Tenancy


class Apartment(BaseModel):
    """
    Apartment Model.
    Fields block and unit number must be unique for every entry.
    Rentable flag describes if the apartment is viewable for other users and tenants looking to book.
    """

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("block", "unit_number")
        permissions = (("view_overview", "Can view the apartments overview status for the semester"),)

    class Block(models.TextChoices):
        NEW = "NEW", "New Block"
        OLD = "OLD", "Old Block"

    block = models.CharField(max_length=10, choices=Block.choices, blank=False, null=False)
    unit_number = models.PositiveSmallIntegerField(blank=False, null=False)
    rent = models.DecimalField(decimal_places=2, max_digits=10, blank=False, null=False)
    rentable = models.BooleanField(default=True, blank=False, null=False, help_text="Viewable and available to rent")

    tenancy_set: models.QuerySet[Tenancy]
    _active_tenant: list[Tenancy]

    def __str__(self) -> str:
        return f"{self.block}-{self.unit_number:02}"

    @property
    def name(self) -> str:
        """
        Representation of the apartment block and number.
        """
        return str(self)

    @property
    def current_tenant(self) -> Tenancy | None:
        """
        Return the current tenant if they exist.
        """
        current = getattr(self, "_active_tenant", None)

        if not current:
            return self.tenancy_set.select_related("user").filter(status__in=active_reserved_defaulting).first()
        return next(iter(current), None)

    @property
    def is_occupied(self) -> bool:
        """
        Whether or not the apartment is currently occupied.
        """
        return bool(self.current_tenant)
