from __future__ import annotations
from typing import TYPE_CHECKING
from common.views import BaseAPIView
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from common.permissions import check_perms
from common.pagination import get_paginated_response
from tenancy import services as sr, serializer as sc, selectors as sl

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.response import Response


class TenancyListCreateView(BaseAPIView):
    class FilterClass(serializers.Serializer):
        period = serializers.CharField()
        search = serializers.CharField()
        status = serializers.CharField()

    permission_classes = [IsAuthenticated]
    serializer_class = sc.TenancyCreateSerializer
    filter_class = FilterClass

    def get(self, request: Request) -> Response:
        check_perms(request.user, "tenancy.view_tenancy")
        filters = self.validate_filter(data=request.query_params)
        qs = sl.tenancy_list_for(user=request.user, filters=filters)
        return get_paginated_response(serializer_class=sc.TenancyListSerializer, queryset=qs, request=request, view=self)

    def post(self, request) -> Response:
        check_perms(request.user, "tenancy.create_tenancy")
        incoming = self.validate_serializer(data=request.data)
        tenancy = sr.tenancy_create(**incoming)
        outgoing = sc.TenancyDetailSerializer(instance=tenancy)
        return Response(data=outgoing.data ,status=status.HTTP_201_CREATED)


class TenancyDetailUpdateDestroyView(BaseAPIView):
    serializer_class = sc.TenancyUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, tenancy_id: int) -> Response:
        check_perms(request.user, "tenancy.view_tenancy")
        tenancy = sl.tenancy_get_for(request.user, tenancy_id)
        outgoing = sc.TenancyDetailSerializer(instance=tenancy)
        return Response(status=status.HTTP_200_OK, data=outgoing.data)

    def delete(self, request, tenancy_id: int) -> Response:
        check_perms(request.user, "tenancy.delete_tenancy")
        selected = sl.tenancy_get_for(request.user , tenancy_id)
        sr.tenancy_terminate(selected)
        return Response(data={"message": "Tenancy Deleted"}, status=status.HTTP_204_NO_CONTENT)

class TenancyOverviewView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pass