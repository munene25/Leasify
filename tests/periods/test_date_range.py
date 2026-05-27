from datetime import date, timedelta
from common.period import *
from dataclasses import FrozenInstanceError
import pytest

@pytest.mark.parametrize(
    "input, output",
    [
        ((date(2024, 1 , 22), date(2024, 1, 25)), (date(2024, 1, 1), date(2024, 1, 31))),
        ((date(2024, 1 , 22), date(2024, 2, 25)), (date(2024, 1, 1), date(2024, 2, 29))),
        ((date(2025, 5 , 31), date(2025, 6, 30)), (date(2025, 5, 1), date(2025, 6, 30))),
        ((date(2026, 2 , 22), date(2026, 2, 25)), (date(2026, 2, 1), date(2026, 2, 28))),
        ((date(2026, 12 , 5), date(2027, 3, 4)), (date(2026, 12, 1), date(2027, 3, 31))),

    ]
)
def test_date_normalization(input: tuple[date, date] , output: tuple[date, date]):
    """
    Normalization should work even in between months.
    I expect to receive the last days of the months for end date and 1st of every start date.
    """
    normalized = normalize_dates(start=input[0], end=input[1])
    assert output == normalized


class TestDateRange:
    def test_post_initialization_checks(self, today: date ):
        """Date range should be normalized and raises if start date occurs after end date"""
        
        r = DateRange(date(2020, 2, 3), date(2020, 2, 20))
        assert r.start_date == date(2020, 2, 1)
        assert r.end_date == date(2020, 2, 29)
        assert r.duration_months == 1
    
        with pytest.raises(ValueError) as exc:
            DateRange(date(2021, 1, 10), date(2020, 2, 1))
        assert  "Start date can only occure before end date" in str(exc.value)

        with pytest.raises(ValueError):
            DateRange(date(2026, 5, 19), date(2026, 5, 18))
        
        r2 = DateRange(today, today)
        assert r2.start_date == today.replace(day=1)
        assert r2.end_date == today.replace(day=monthrange(today.year, today.month)[1])
        assert r2.duration_months == 1

        r3 = DateRange(date(2024, 4, 30), date(2025, 4, 30))
        assert r3.start_date == date(2024, 4, 1)
        assert r3.end_date == date(2025, 4, 30)
        assert r3.duration_months == 13


    def test_date_range_frozen(self, today: date):
        r = DateRange(today, today)
        with pytest.raises(FrozenInstanceError):
            r.start_date = today # type: ignore
        with pytest.raises(FrozenInstanceError):
            r.duration_months = 3 # type: ignore
        with pytest.raises(FrozenInstanceError):
            r.end_date += timedelta(days=4) # type: ignore

    def test_for_month(self, today: date):
        """Should return accurate start and end dates"""
        
        # Date range should be normalized
        d1 = date(2021, 2, 4)
        r1 = DateRange.for_month(d1)
        assert r1.start_date == date(2021, 2, 1)
        assert r1.end_date == date(2021, 2, 28)
        assert r1.duration_months == 1

        # Without date input should default to current month
        # This should be equivalent to a date range of the month containing today
        this_month = DateRange.for_month()
        month_today = DateRange(today, today)
        assert this_month == month_today
        
        d2 = date(2020, 2, 29)
        r2 = DateRange.for_month(d2)
        assert r2.duration_months == 1
        assert r2.start_date == d2.replace(day=1)
        assert r2.end_date == d2



    def test_month_shifting(self):
        """Start dates and end dates are shifted based on delta"""
        today = date(2026, 2, 28)
        curr_month = DateRange.for_month(today)

        # Extend start by one month
        backward_extension = -1
        start_shifted = curr_month.shift_months(backward_extension, 0)
        assert start_shifted != curr_month
        assert start_shifted.start_date == date(2026, 1, 1)
        assert start_shifted.end_date == curr_month.end_date
        assert start_shifted.duration_months == abs(backward_extension) + curr_month.duration_months


        undone_shift = start_shifted.shift_months(+1, 0)
        assert undone_shift == curr_month

        # Extend end date by one month
        forward_extension = +2
        end_shifted = curr_month.shift_months(0, forward_extension)
        assert end_shifted.end_date == date(2026, 4, 30)
        assert end_shifted.start_date == curr_month.start_date
        assert end_shifted.duration_months == forward_extension + curr_month.duration_months

        # Try a bad shift
        with pytest.raises(ValueError):
            curr_month.shift_months(+1, 0)

        with pytest.raises(ValueError):
            curr_month.shift_months(+1, -1)

    
    def test_compute_lease_window(self):
        """
        Should fail for 0 values.
        Should quantize the days properly.
        End dates and Start dates should be computed correctly.
        """
        t1, d1 = date(2024, 1, 31), 1
        r1 = DateRange.compute_lease_window(t1, d1)
        assert r1.start_date == date(2024, 1, 1)
        assert r1.duration_months == d1
        assert r1.end_date == t1

        t2, d2 = date(2024, 1, 30), 2
        r2 = DateRange.compute_lease_window(t2, d2)
        assert r2.start_date == date(2024, 1, 1)
        assert r2.duration_months == d2
        assert r2.end_date == date(2024, 2, 29)

        t3, d3 = date(2026, 1, 1), 0
        with pytest.raises(ValueError):
            DateRange.compute_lease_window(t3, d3)

    def test_compute_month_shifts(self):
        """Next and Previous month computations"""
        t1 = date(2026, 1, 1)
        curr_month = DateRange.for_month(t1)
        
        next_month = curr_month.next_month()
        assert next_month != curr_month
        assert next_month.start_date == date(2026, 2, 1)
        assert next_month.duration_months == 1
        assert next_month.end_date == date(2026, 2, 28)

        prev_month = curr_month.previous_month()
        assert prev_month != curr_month
        assert prev_month.start_date == date(2025, 12, 1)
        assert prev_month.duration_months == 1
        assert prev_month.end_date == date(2025, 12, 31)

        two_months = curr_month.shift_months(0, +1)
        with pytest.raises(ValueError) as exc:
            two_months.next_month()
        assert "Duration provided is not a month" in str(exc.value)
        with pytest.raises(ValueError) as exc:
            two_months.previous_month()

    def test_compute_month_shifts_at_end_year(self):
        """Assert that end year month computations resolve correctly"""
        t1 = date(2020, 11, 1)
        curr_month = DateRange.for_month(t1)
        two_months_later = curr_month.shift_months(0, +2)
        assert two_months_later.start_date == t1
        assert two_months_later.end_date.year == t1.year + 1

    def test_compute_range_with_grace_period(self):
        """
        Compute the monthly date range with a grace period
        If date falls within the grace period, the date range will include the previous month
        in the range else only this months range is given.
        """
        
        d1 = date(2026, 8, 5)
        d2 = d1.replace(day=7)
        d3 = d1.replace(day=11)
        start_date = date(2026, 8, 1)
        prev_start_date = start_date.replace(month=7)
        end_date = d1.replace(day=31)

        r1 = DateRange.with_grace_period(d1)
        assert r1.start_date == prev_start_date
        assert r1.duration_months == 2
        assert r1.end_date == end_date

        r2 = DateRange.with_grace_period(d2)
        assert r2.start_date == prev_start_date
        assert r2.duration_months == 2
        assert r2.end_date == end_date

        r3 = DateRange.with_grace_period(d3)
        assert r3.start_date == start_date
        assert r3.duration_months == 1
        assert r3.end_date == end_date


class TestPartialRange:
    @pytest.mark.parametrize(
        "string,start,end,duration",
        [
            ("start=2021-MAY,end=2022-MAY", date(2021, 5, 1), date(2022, 5, 31), 13),
            ("start=2025-JAN,end=2025-DEC", date(2025, 1, 1), date(2025, 12, 31), 12),
        ]
    )
    def test_string_parsing(self, string: str, start: date, end: date, duration: int): 
        """First need to test if it parses correctly"""
        pr = PartialRange.from_string(string)
        assert pr.start == start
        assert pr.end == end
        # assert pr.duration_months == duration