from functools import wraps
from typing import Callable, Any
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound


def not_found(field:str, message: str):
    """
    A clean wrapper for attatching error messages to not found exceptions
    """
    def wrapper(func: Callable[..., Any]):
        @wraps(func)
        def wrapped(*args, **kwargs):
            try: 
                return func(*args, **kwargs)
            except ObjectDoesNotExist as exc:
                raise NotFound({field: message}) from exc
        return wrapped
    return wrapper