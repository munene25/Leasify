from __future__ import annotations
from functools import cached_property
from django.db import models
from rest_framework.exceptions import ValidationError
from mixins.model_full_clean_mixin import ModelExceptionMixin
from django.utils import timezone

class Semester(ModelExceptionMixin, models.Model):
    """
    Semester model
    Refactored to remove the name as a primary attribute
    Name can either be the cannonical name or the provided alternative name used for meta_data
    """

    alt_name = models.CharField(max_length=50, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    off_season = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        unique_together = ("start_date", "end_date")

    @property
    def active(self):
        return self.start_date <= timezone.localdate() <= self.end_date

    def clean(self) -> None:
        # start_date should come before end_date
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            error = ["Invalid dates. start_date cannot appear on or before end_date"]
            raise ValidationError({"end_date": error, "start_date": error})

    @cached_property
    def cannonical_name(self) -> str:
        s_month = self.start_date.strftime("%b").upper()
        e_month = self.end_date.strftime("%b").upper()
        year = self.start_date.year
        return f"{s_month}-{e_month}-{year}"

    def __str__(self) -> str:
        return self.cannonical_name

    @property
    def name(self):
        return self.alt_name or self.cannonical_name
