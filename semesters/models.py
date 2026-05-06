from functools import cached_property
from django.db import models
from rest_framework.exceptions import ValidationError
from common.models import BaseModel
from django.utils import timezone
from datetime import date, timedelta, datetime

GRACE_PERIOD = timedelta(weeks=2)


class Semester(BaseModel):
    """
    Semester model
    Refactored to remove the name as a primary attribute
    Name can either be the cannonical name or the provided alternative name used for meta_data
    """

    class Meta:
        ordering = ["-start_date"]
        unique_together = ("start_date", "end_date")

    alt_name = models.CharField(max_length=50, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    off_season = models.BooleanField()
    
    @staticmethod
    def get_date_range(value: str) -> tuple[date, date]:
        """
        Returns a date range from a string with format YYYY-MMM-MMM
        Year is always provided but start_month and end_month have a default of JAN and DEC
        """

        from calendar import monthrange

        MONTHS = {
            "JAN": 1, "FEB": 2,
            "MAR": 3, "APR": 4,
            "MAY": 5, "JUN": 6,
            "JUL": 7, "AUG": 8,
            "SEP": 9, "OCT": 10,
            "NOV": 11, "DEC": 12,
        }

        parts = value.split("-")
        year = int(parts[0])

        try:
            start_month, end_month = MONTHS[parts[1][:3].upper()], MONTHS[parts[2][:3].upper()]
        except (KeyError, IndexError):
            start_month, end_month = 1, 12

        range = date(year, start_month, 1), date(year, end_month, monthrange(year, end_month)[1])
        return range
    
    @property
    def active(self):
        return self.start_date <= timezone.now().date() <= self.end_date

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
        return f"{year}-{s_month}-{e_month}"

    def __str__(self) -> str:
        return self.cannonical_name

    @property
    def name(self):
        return self.alt_name or self.cannonical_name

    @property
    def has_ended(self):
        """Check if the semester has ended"""
        
        return bool(timezone.now().date() > self.end_date)
    
