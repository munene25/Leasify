from __future__ import annotations
from typing import TYPE_CHECKING
from common.views import BaseAPIView
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from common.permissions import check_perms
from common.pagination import get_paginated_response
from tenancy import services as sr, serializer as sc, selectors as sl
from tenancy.choices import TenancyStatus as TS, TerminationReason as TR

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.response import Response


class TenancyListCreateView(BaseAPIView):
    class FilterClass(serializers.Serializer):
        date_joined = serializers.CharField()
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
        incoming = self.validate_serializer(data=request.data)
        tenancy = sr.tenancy_create(**incoming)
        outgoing = sc.TenancyDetailSerializer(instance=tenancy)
        return Response(data=outgoing.data ,status=status.HTTP_201_CREATED)

class TenancyDetailUpdateView(BaseAPIView):
    serializer_class = sc.TenancyLeaseExtensionSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, tenancy_id: int) -> Response:
        check_perms(request.user, "tenancy.view_tenancy")
        tenancy = sl.tenancy_get_for(request.user, tenancy_id)
        outgoing = sc.TenancyDetailSerializer(instance=tenancy)
        return Response(status=status.HTTP_200_OK, data=outgoing.data)

    def patch(self, request, tenancy_id: int) -> Response:
        check_perms(request.user, "tenancy.change_tenancy")
        incoming = self.validate_serializer(data=request.data)
        selected = sl.tenancy_get_for(request.user , tenancy_id)

        sr.tenancy_lease_extend(selected, **incoming)
        return Response(data={"message": "Lease extended"}, status=status.HTTP_204_NO_CONTENT)


class TenancyTerminateView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = sc.TenancyTerminateSerializer

    def get(self, request):

        return Response(data={"termination_reasons": [TR.MANAGERIAL, TR.NONPAYMENT, TR.VOLUNTARY]})
    
    def post(self, request, tenancy_id: int):
        check_perms(request.user, "tenancy.change_tenancy")
        selected = sl.tenancy_get_for(request.user , tenancy_id)
        
        if selected.user == request.user:
            reason = TR.VOLUNTARY
        else:
            reason = self.validate_serializer(data=request.data)["termination_reason"]
        
        sr.tenancy_terminate(tenancy=selected, termination_reason=reason)
        return Response(data={"message": "Lease extended"}, status=status.HTTP_204_NO_CONTENT)

class TenancyOverviewView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pass