from rest_framework.request import Request
from rest_framework.views import View
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, ScopedRateThrottle
from structlog import get_logger


logger = get_logger("throttling")


class BaseThrottle(ScopedRateThrottle):
    """Base throttle with logging."""
    scope_attr = "throttle_scope"

    def allow_request(self, request: Request, view: View) -> bool:
        allowed = super().allow_request(request, view)
        if not allowed:
            logger.warning(
                "request_throttled",
                scope=self.scope,
                rate=self.get_rate(),
            )
        return allowed


class EmailThrottle(BaseThrottle):
    """Throttle by email address from request data or authenticated user."""

    def get_cache_key(self, request: Request, view: View) -> str | None:
        ident = (
            request.data.get("email")
            or (request.user.email if request.user.is_authenticated else None)
        )
        if ident is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}


class UserSustained(BaseThrottle, UserRateThrottle):
    scope = "user_sustained"


class AnonSustained(BaseThrottle, AnonRateThrottle):
    scope = "anon_sustained"