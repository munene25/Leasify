from __future__ import annotations
from typing import TYPE_CHECKING
from common.views import BaseAPIView
from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from common.permissions import check_perms
from common.pagination import get_paginated_response
from tenancy import services as sr, serializer as sc, selectors as sl
from tenancy.choices import TenancyStatus as TS, TerminationReason as TR

if TYPE_CHECKING:
    from rest_framework.request import Request


class TenancyListCreateView(BaseAPIView):
    class FilterClass(serializers.Serializer):
        joined_before = serializers.DateField()
        joined_after = serializers.DateField()
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
        tenancy = sr.tenancy_create(user=request.user, **incoming)
        outgoing = sc.TenancyDetailSerializer(instance=tenancy)
        return Response(data=outgoing.data, status=status.HTTP_201_CREATED)


class TenancyDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = sc.TenancyLeaseExtensionSerializer

    def get(self, request, tenancy_id: int) -> Response:
        check_perms(request.user, "tenancy.view_tenancy")
        selected = sl.tenancy_get_for(request.user, tenancy_id)
        outgoing = sc.TenancyDetailSerializer(instance=selected)
        return Response(status=status.HTTP_200_OK, data=outgoing.data)


class TenancyTerminateView(BaseAPIView):
    serializer_class = sc.TenancyTerminateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, tenancy_id: int):
        check_perms(request.user, "tenancy.change_tenancy")
        selected = sl.tenancy_get_for(request.user, tenancy_id)

        if selected.status != TS.TERMINATED:
            args = (
                {"termination_reason": TR.VOLUNTARY, "termination_date": None}
                if selected.user == request.user
                else self.validate_serializer(data=request.data)
            )

            selected = sr.tenancy_terminate(tenancy=selected, **args)
        outgoing = sc.TenancyDetailSerializer(instance=selected)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class TenancyLeaseExtensionView(BaseAPIView):
    serializer_class = sc.TenancyLeaseExtensionSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, tenancy_id: int):
        check_perms(request.user, "tenancy.change_tenancy")
        selected = sl.tenancy_get_for(request.user, tenancy_id)
        incoming = self.validate_serializer(data=request.data)
        _, billing = sr.tenancy_lease_extend(tenancy=selected, **incoming)
        return Response(data={"message": f"Lease {billing.name} created", "billing_id": billing.pk}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_tenancy_termination_reasons(request):
    reasons = [{"key": reason.value, "display": reason.label} for reason in TR]
    return Response(data=reasons, status=status.HTTP_200_OK)


class TenancyOverviewView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pass
