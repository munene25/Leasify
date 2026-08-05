from rest_framework.authentication import SessionAuthentication as RestSessionAuthentication

class SessionAuthentication(RestSessionAuthentication):
    """
    Allow 401 status codes
    
    Violates the protocols but necessary to signal authentication failures
    """
    def authenticate_header(self, request):
        return "session"
    
class ForceCSRFAuthentication(SessionAuthentication):
    def authenticate(self, request):
        self.enforce_csrf(request)
        return super().authenticate(request)