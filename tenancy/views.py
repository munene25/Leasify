from common.views import BaseAPIView
from rest_framework.response import Response
from rest_framework import status
from tenancy import services as sr, serializer as sc, selectors as sl

class TenancyListCreateView(BaseAPIView):
    serializer_class = TenancyCreateSerializer

    def get(self, request) -> Response:
        tenancies = tenancy_list()
        serializer = TenancyListSerializer(instance=tenancies, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def post(self, request) -> Response:
        data = self.validate_serializer(data=request.data)
        service = TenancyService()
        service.create(**data)
        return Response(status=status.HTTP_201_CREATED)


class TenancyDetailUpdateDestroyView(BaseAPIView):
    serializer_class = TenancyUpdateSerializer

    def get(self, request, tenancy_id: int) -> Response:
        tenancy = tenancy_get_by_id(tenancy_id)
        serializer = TenancyDetailSerializer(instance=tenancy)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def put(self, request, tenancy_id: int) -> Response:
        data = self.validate_serializer(data=request.data)
        service = TenancyService(tenancy_id)
        service.update(**data)
        return Response(status=status.HTTP_200_OK)

    def patch(self, request, tenancy_id: int) -> Response:
        data = self.validate_serializer(data=request.data, partial=True)
        service = TenancyService(tenancy_id)
        service.update(**data)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, tenancy_id: int) -> Response:
        service = TenancyService(tenancy_id)
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
