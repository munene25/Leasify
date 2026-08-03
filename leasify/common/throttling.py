from structlog import get_logger

from rest_framework.throttling import ScopedRateThrottle

logger = get_logger("throttling")


class ScopedThrottle(ScopedRateThrottle):
    scope_attr = "throttle_scope"

    def allow_request(self, request, view) -> bool:
        """Add logging to Scoped Rate Throttle"""
        if not (allowed := super().allow_request(request, view)):
            logger.warning(
                "request_throttled",
                scope=self.scope,
                rate=self.get_rate(),
                identity=self.get_ident(request),
            )
        return allowed


class EmailThrottle(ScopedThrottle):
    """
    Throttle by email address from request data.
    Redundant to use email if user already authenticated, in such a case just use email
    """

    def get_cache_key(self, request, view) -> str | None:
        
        ident = request.data.get("email")
        if ident is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}
