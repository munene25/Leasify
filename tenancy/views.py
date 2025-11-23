from rest_framework.views import APIView
from .serializer import (
    TenancyListSerializer,
    TenancyCreateSerializer,
    TenancyDetailSerializer,
    TenancyUpdateSerializer
)
from .services import (
    TenancyCreateService,
    TenancyUpdateService,
    TenancyDeleteService
)

class TenancyListCreateView(APIView):
    pass