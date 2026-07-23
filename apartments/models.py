from typing import TYPE_CHECKING
from django.db import models
from common.models import BaseModel
from tenancy.choices import ACTIVE_RESERVED_OR_DEFAULTING
from apartments.choices import Block, Wing

if TYPE_CHECKING:
    from tenancy.models import Tenancy


class Apartment(BaseModel):
    """
    Apartment Model.
    Fields block and unit number must be unique for every entry.
    Rentable flag describes if the apartment is viewable for primary users.
    """

    class Meta:
        ordering = ["-created_at"]
        unique_together = "block", "unit_number"

    block = models.CharField(max_length=10, choices=Block.choices, blank=False, null=False)
    unit_number = models.PositiveSmallIntegerField(blank=False, null=False)
    floor = models.PositiveSmallIntegerField(blank=False, null=False, help_text="Floor number, 0 for ground floor")
    rent = models.DecimalField(decimal_places=2, max_digits=10, blank=False, null=False)
    rentable = models.BooleanField(default=True, blank=False, null=False, help_text="Viewable and available to rent")

    wing = models.CharField(max_length=15, blank=True, null=True, choices=Wing.choices)

    tenancy_set: models.QuerySet["Tenancy"]
    _active_tenant: list["Tenancy"]

    def __str__(self) -> str:
        """Simplified representation of the apartment"""
        return f"Block-{self.block} Unit-{self.unit_number:02}"

    @property
    def name(self) -> str:
        """Full represantation of the aparment block, unit_number, floor, wing."""

        parts = [f"Unit {self.block}-{self.floor}{self.unit_number:02}"]
        if self.wing:
            parts.append(f"{self.wing.capitalize()} wing")
        return " | ".join(parts)

    @property
    def current_tenant(self) -> "Tenancy | None":
        """Return the current tenant if they exist."""

        if current:= getattr(self, "_active_tenant", None):
            return current[0]
        return self.tenancy_set.select_related("user").filter(status__in=ACTIVE_RESERVED_OR_DEFAULTING).first()

    @property
    def is_occupied(self) -> bool:
        """Whether or not the apartment is currently occupied."""
        return bool(self.current_tenant)
