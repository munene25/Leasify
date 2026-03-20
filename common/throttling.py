import hashlib
from typing import override
from typing import Protocol
from rest_framework.request import Request
from rest_framework.views import View
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, ScopedRateThrottle
from logging import getLogger


logger = getLogger("throttling")


class ThrottleProtocol(Protocol):
    @property
    def scope(self) -> str: ...
    def allow_request(self, request, view) -> bool: ...
    def get_rate(self) -> str: ...
    def get_cache_key(self, request, view) -> str: ...


class ThrottleMixin:
    """Adds logs and stashes the key in the request object"""
    def allow_request(self: ThrottleProtocol, request: Request, view: View):
        allowed = super().allow_request(request, view)
        setattr(request, "throttle_cache_key", self.get_cache_key(request, view))
        if not allowed:
            scope = self.scope or getattr(view, "throttle_scope", "undefined")
            logger.warning(f"Throttled. [scope: {scope}] [rate: {self.get_rate()}]")
        return allowed


class EmailScopedThrottle(ThrottleMixin, ScopedRateThrottle):
    @override
    def get_cache_key(self, request, view):
        # Realized this throttles even on successful attempts
        # like login or requesting email verifications
        email_from_data = request.data.get("email", None)
        user_email = request.user.email if request.user and request.user.is_authenticated else None
        ident = email_from_data or user_email
        if ident is None:
            return None
        cache_key = self.cache_format % {"scope": self.scope, "ident": ident}
        return cache_key


class UserSustained(ThrottleMixin, UserRateThrottle):
    scope = "user_sustained"


class AnonSustained(ThrottleMixin, AnonRateThrottle):
    scope = "anon_sustained"


