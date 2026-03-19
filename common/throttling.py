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


class ThrottleLogsMixin:
    def allow_request(self: ThrottleProtocol, request: Request, view: View):
        allowed = super().allow_request(request, view)
        if not allowed:
            scope = self.scope or getattr(view, "throttle_scope", "undefined")
            logger.warning(f"Throttled. [scope: {scope}] [rate: {self.get_rate()}]")
        return allowed


class EmailScopedThrottle(ThrottleLogsMixin, ScopedRateThrottle):
    @override
    def get_cache_key(self, request, view):
        # Realized this throttles even on successful attempts
        # like login or requesting email verifications
        email = request.data.get("email")
        if not email:
            return None
        ident = hashlib.sha256(email.lower().encode()).hexdigest()
        cache_key = self.cache_format % {"scope": self.scope, "ident": ident}
        setattr(view, "throttle_cache_key", cache_key)
        return cache_key


class UserSustained(ThrottleLogsMixin, UserRateThrottle):
    scope = "user_sustained"


class AnonSustained(ThrottleLogsMixin, AnonRateThrottle):
    scope = "anon_sustained"
