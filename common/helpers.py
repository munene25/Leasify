from functools import wraps
from typing import Callable, Any, TypeVar
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound
from datetime import date

R = TypeVar("R")

def raise_not_found(field: str, message: str) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """
    A clean wrapper for attaching error messages to not found exceptions
    """

    def wrapper(func: Callable[..., R]) -> Callable[..., R]:
        @wraps(func)
        def wrapped(*args, **kwargs) -> R:
            try:
                return func(*args, **kwargs)
            except ObjectDoesNotExist as exc:
                raise NotFound({field: message}) from exc

        return wrapped

    return wrapper


def parse_date_range(range: str, sep: str = ",")-> dict[str, date|None]:
    """
    Parse a period range from string into dates.
    Periods are defined by start and stop and accepts either.
    
    :param range: the range represented in string format e.g. "start=2000-MAY,stop=2001-JUN"
    :param sep: the seperator used to seperate the two date ranges
    """

    from calendar import monthrange
    #Example range: start=2000-MAY,stop=2001-JUN

    MONTHS = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
        "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
        "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
    }

    dates: dict[str, date|None] = {"start": None, "stop": None}
    
    ranges = range.split(sep)

    for r in ranges:
        edge, year_month = r.split("=")
        year_str, month_str = year_month.split("-")
        year = int(year_str)
        month = MONTHS[month_str]
        day = 1 if edge == "start" else monthrange(year, month)[1]
        dates[edge] = date(year, month, day)
    return dates