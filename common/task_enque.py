from typing import Callable
from functools import wraps
from celery.exceptions import OperationalError

def safe_task(func: Callable):
    """
    Wrap celery delay calls incase the broker is down
    Add logging feature for unlogged wraps
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OperationalError:
            from structlog import getLogger
            logger = getLogger("tasks")
            logger.error(f"Could not enque task [{func.__name__}]. Cache might be down or misconfigured")
    return wrapper