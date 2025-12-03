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
    
    def __str__(self):
        return f"Name: {self.name}"

    @property
    def active(self):
        return self.start_date <= date.today() <= self.end_date
