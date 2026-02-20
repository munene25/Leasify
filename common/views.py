from typing import override, Any
from rest_framework.views import APIView
from ipware import get_client_ip
import structlog

class BaseAPIView(APIView):
    @override
    def perform_authentication(self, request):
        super().perform_authentication(request)
        structlog.contextvars.bind_contextvars(
                user_id=request.user.pk if request.user.is_authenticated else None,
                ip=get_client_ip(request),
            )