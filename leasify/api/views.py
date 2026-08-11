from rest_framework import status
from rest_framework.response import Response

from leasify.common.views import BaseAPIView
from leasify.api.health import *

class HealthCheckView(BaseAPIView):
    """Health check for the api and dependencies"""

    def get(self, request) -> Response:
        checks = {
            "db": check_db(),
            "redis": check_redis(),
            "celery": check_celery(),
        }
        healthy = all(v == "ok" for v in checks.values())
        checks["status"] = "ok" if healthy else "dedgraded"
        return Response(
            checks,
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

