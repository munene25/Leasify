from dataclasses import dataclass, field
from datetime import date
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from calendar import monthrange

today = lambda: timezone.now().date()

def normalize_dates(*, start: date, end: date) -> tuple[date, date]:
    """Normalize start and end dates to 1st of the month and last day of the month"""
    start_date = start.replace(day=1)
    last_day_of_end_month = monthrange(end.year, end.month)[1]
    end_date = end.replace(day=last_day_of_end_month)
    return start_date, end_date

def compute_month_diff(start: date, end: date) -> int:
    d = relativedelta(end, start)
    return (d.years * 12 + d.months + 1)

@dataclass(frozen=True)
class DateRange:
    start_date: date
    end_date: date
    duration_months: int = field(init=False)

    def __post_init__(self) -> None:
        """Calculate the duration in months of the date ranges"""

        if self.start_date > self.end_date:
            raise ValueError("Start date can only occure before end date")

        s, e = normalize_dates(start=self.start_date, end=self.end_date)
        object.__setattr__(self, "start_date", s)
        object.__setattr__(self, "end_date", e)
        object.__setattr__(self, "duration_months", compute_month_diff(s, e))

    def __eq__(self, value: "DateRange") -> bool:
        if not isinstance(value, DateRange):
            raise ValueError("Can only perfom comparisons for DateRange objects")
        return (
            self.start_date == value.start_date
            and self.end_date == self.end_date
            and self.duration_months == value.duration_months
        )

    def shift_months(self, start_delta: int, end_delta: int) -> "DateRange":
        """Shift the start_month or end_month by delta"""

        s = self.start_date + relativedelta(months=start_delta)
        e = self.end_date + relativedelta(months=end_delta)
        return DateRange(s, e)

    def next_month(self) -> "DateRange":
        """Get date ranges of the next month"""
        if self.duration_months > 1:
            raise ValueError("Duration provided is not a month")
        return self.shift_months(+1, +1)

    def previous_month(self) -> "DateRange":
        """Get date ranges of the previous month"""
        if self.duration_months > 1:
            raise ValueError("Duration provided is not a month")
        return self.shift_months(-1, -1)

    @classmethod
    def for_month(cls, date: date | None = None) -> "DateRange":
        """Get the date ranges for the month. Defaults to month containing today's date"""
        date = date or today()
        return cls(date, date)

    @classmethod
    def compute_lease_window(cls, start_date: date, duration_months: int) -> "DateRange":
        """Return normalized lease period for the tenancy"""

        if duration_months < 1:
            raise ValueError("Minimum lease period is 1 month")
        r = cls.for_month(start_date)
        return r.shift_months(0, duration_months - 1)

    @classmethod
    def with_grace_period(cls, date: date | None = None) -> "DateRange":
        """If the date is within the GRACE_PERIOD window, a buffer is applied to the start date"""

        from tenancy.models import GRACE_PERIOD

        date = date or today()
        month_date_range = cls.for_month(date)
        if date.day <= GRACE_PERIOD.days:
            return month_date_range.shift_months(-1, 0)
        return month_date_range


@dataclass
class PartialRange:
    start: date | None = None
    end: date | None = None
    duration_months: int | None = None

    def __post_init__(self):
        if self.start and self.end:
            if self.end < self.start:
                raise ValueError("Start date can only occure before end date")
            self.duration_months = compute_month_diff(self.start, self.end)

    @classmethod
    def from_string(cls, range: str, sep: str = ",") -> "PartialRange":
        """
        Parse a period range from string into dates.
        Periods are defined by start and end and accepts either.

        :param range: the range represented in string format"
        :param sep: the seperator used to seperate the two date ranges
        """
        # Example range: start=2000-MAY,end=2001-JUN

        MONTHS = {
            "JAN": 1,"FEB": 2,"MAR": 3,"APR": 4,
            "MAY": 5,"JUN": 6,"JUL": 7,"AUG": 8,
            "SEP": 9,"OCT": 10,"NOV": 11,"DEC": 12,
        }

        pr = cls()

        ranges = range.split(sep, maxsplit=1)

        for s in ranges:
            edge, year_month = s.split("=")
            year_str, month_str = year_month.split("-")

            year, month = int(year_str), MONTHS[month_str]
            
            day = 1 if edge == "start" else monthrange(year, month)[1]
            if edge in {"start", "end"}:
                setattr(pr, edge, date(year, month, day))
        return pr
