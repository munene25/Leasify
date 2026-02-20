import hashlib
from typing import Protocol 
from rest_framework.request import Request
from rest_framework.views import View
from users.models import User
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, ScopedRateThrottle
from logging import getLogger


logger = getLogger("throttling")

class ThrottleProtocol(Protocol):
    @property
    def scope(self) -> str: ...
    def allow_request(self, request, view) -> bool: ...
    def get_rate(self) -> str: ...
    


class ThrottleLoggingMixin:
    def allow_request(self: ThrottleProtocol, request: Request, view: View):
        allowed = super().allow_request(request, view)
        if not allowed:
            scope = self.scope or getattr(view, "throttle_scope", "undefined")
            logger.warning(f"Throttled. [scope: {scope}] [rate: {self.get_rate()}]")
        return allowed
    
    
class EmailBaseThrottle(ThrottleLoggingMixin, ScopedRateThrottle):
    def get_cache_key(self, request, view):
        # Realized this throttles even on successful attempts 
        # like login or requesting email verifications
        email = request.data.get('email')
        if not email: return None
        ident = hashlib.sha256(email.lower().encode()).hexdigest()
        return self.cache_format % {'scope': self.scope, 'ident': ident}
    

class UserBurst(ThrottleLoggingMixin, UserRateThrottle):
    scope = 'user_burst'

class UserSustained(ThrottleLoggingMixin, UserRateThrottle):
    scope = 'user_sustained'

class AnonBurst(ThrottleLoggingMixin, AnonRateThrottle):
    scope = 'anon_burst'

class AnonSustained(ThrottleLoggingMixin, AnonRateThrottle):
    scope = 'anon_sustained'
