from __future__ import annotations
from datetime import date
from django.db import models
from rest_framework.exceptions import NotFound

class Semester(models.Model):
    """
    This is the standalone semester model.
    """

    name = models.CharField(max_length=12, blank=False, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    off_season = models.BooleanField()
    rent = models.DecimalField(decimal_places=2, max_digits=10)

    def __str__(self):
        return f"Name: {self.name}"

    @classmethod
    def current_semester(cls) -> Semester:
        try: 
            return cls.objects.get(
            start_date__lte=date.today(), end_date__gte=date.today()
        )
        except Semester.DoesNotExist:
            raise NotFound({"current_semester": [f"Semester not found, please create a semester for this time period"]})

    @property
    def active(self):
        return self.start_date <= date.today() <= self.end_date
