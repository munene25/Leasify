from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from mixins.view_validation_mixin import ValidateSerializerMixin
from .services import TenancyService
from .selectors import tenancy_list, tenancy_get_by_id
from .serializer import (
    TenancyListSerializer,
    TenancyCreateSerializer,
    TenancyDetailSerializer,
    TenancyUpdateSerializer,
)
from .tasks import show_detail

class TenancyListCreateView(APIView, ValidateSerializerMixin):
    serializer_class = TenancyCreateSerializer

    def get(self, request) -> Response:
        tenancies = tenancy_list()
        print(tenancies)
        serializer = TenancyListSerializer(instance=tenancies, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def post(self, request) -> Response:
        data = self.validate_input(data=request.data)
        service = TenancyService()
        service.create(**data)
        return Response(status=status.HTTP_201_CREATED)


class TenancyDetailUpdateDestroyView(APIView, ValidateSerializerMixin):
    serializer_class = TenancyUpdateSerializer

    def get(self, request, tenancy_id: int) -> Response:
        tenancy = tenancy_get_by_id(tenancy_id)
        show_detail.delay(tenancy_id)
        serializer = TenancyDetailSerializer(instance=tenancy)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def put(self, request, tenancy_id: int) -> Response:
        data = self.validate_input(data=request.data)
        service = TenancyService(tenancy_id)
        service.update(**data)
        return Response(status=status.HTTP_200_OK)

    def patch(self, request, tenancy_id: int) -> Response:
        data = self.validate_input(data=request.data, partial=True)
        service = TenancyService(tenancy_id)
        service.update(**data)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, tenancy_id: int) -> Response:
        service = TenancyService(tenancy_id)
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
