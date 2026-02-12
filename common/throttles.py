import hashlib
from rest_framework.throttling import AnonRateThrottle
from rest_framework.throttling import UserRateThrottle, ScopedRateThrottle

class EmailBaseThrottle(ScopedRateThrottle):
    def get_cache_key(self, request, view):
        email = request.data.get('email')
        if not email: return None
        ident = hashlib.sha256(email.lower().encode()).hexdigest()
        return self.cache_format % {'scope': self.scope, 'ident': ident}
    

class UserBurst(UserRateThrottle):
    scope = 'user_burst'

class UserSustained(UserRateThrottle):
    scope = 'user_sustained'

class AnonBurst(AnonRateThrottle):
    scope = 'anon_burst'

class AnonSustained(AnonRateThrottle):
    scope = 'anon_sustained'
