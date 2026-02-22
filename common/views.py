from typing import override
from rest_framework.views import APIView
import structlog
from django.contrib.auth.models import AbstractUser
from contextvars import ContextVar

class BaseAPIView(APIView):
    @override
    def perform_authentication(self, request):
        super().perform_authentication(request)
        structlog.contextvars.bind_contextvars(
            user_id= request.user.pk if  request.user.is_authenticated else None,
        )


