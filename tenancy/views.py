from rest_framework.views import APIView
from .serializer import (
    TenancyListSerializer,
    TenancyCreateSerializer,
    TenancyDetailSerializer,
    TenancyUpdateSerializer
)

class TenancyListCreateView(APIView):
    pass