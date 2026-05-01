from functools import wraps
from typing import Callable, Any, TypeVar
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound


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