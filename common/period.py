from dataclasses import dataclass, field
from datetime import date
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from typing import Self


@dataclass
class DateRange:
    start_date: date
    end_date: date
    duration_months: int = field(init=False)

    def __post_init__(self):
        print(f"START: {self.start_date} END: {self.end_date}")
        if self.start_date >= self.end_date:
            raise ValueError("start date can only occur before the end date")
        self.duration_months = relativedelta(self.start_date, self.end_date).months + 1
        


    def normalize_dates(self) -> None:
        """Normalize start and end dates to 1st of the month and last day of the month"""
        self.start_date.replace(day=1)
        last_day_of_end_month = monthrange(self.end_date.year, self.end_date.month)[1]
        self.end_date.replace(day=last_day_of_end_month)

    def shift_months(self, start_delta: int, end_delta: int) -> "DateRange":
        """Shift the start_month or end_month by delta"""
        shift_start = relativedelta(months=start_delta)
        shift_end = relativedelta(months=end_delta)

        start_date = self.start_date + shift_start
        end_date = self.end_date + shift_end
        date_range = DateRange(start_date, end_date)
        date_range.normalize_dates()
        return date_range

    @classmethod
    def for_month(cls, date: date) -> "DateRange":
        """Get the date ranges for the month"""

        start_date = date.replace(day=1)
        last_day_of_end_month = monthrange(start_date.year, start_date.month)[1]
        end_date = date.replace(day=last_day_of_end_month)
        return cls(start_date, end_date)
    
    @classmethod
    def compute_lease_window(cls, start_date: date, duration_months: int) -> "DateRange":
        """Return normalized lease period for the tenancy"""
        d = duration_months - 1
        if d < 0:
            raise ValueError("Minimum lease period is 1 month")
        date_range = cls.for_month(start_date)
        return date_range.shift_months(0, d)
    

    @classmethod
    def with_grace_period(cls, date: date) -> "DateRange":
        """If the date is within the GRACE_PERIOD window, a buffer is applied to the start date"""

        from tenancy.models import GRACE_PERIOD
        
        month_date_range = cls.for_month(date)

        if date.day <= GRACE_PERIOD.days:
            month_date_range.shift_months(-1, 0)
        
        return month_date_range
        
    
    def next_month(self) -> "DateRange":
        """Get date ranges of the next month"""
        if self.duration_months > 1:
            raise ValueError("The duration range is not a month")
        return self.shift_months(+1, +1)
    

    def previous_month(self) -> "DateRange":
        """Get date ranges of the previous month"""
        if self.duration_months > 1:
            raise ValueError("The duration range is not a month")
        return self.shift_months(-1, -1)