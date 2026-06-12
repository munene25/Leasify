from common.views import BaseAPIView
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from common.permissions import check_perms
from common.pagination import get_paginated_response
from billing import serializer as sc, services as sr, selectors as sl

class BillingListView(BaseAPIView):
    class FilterClass(serializers.Serializer):
        period_from = serializers.DateField()
        period_to = serializers.DateField()
        is_current = serializers.BooleanField(allow_null=True)
        search = serializers.CharField()
        search = serializers.CharField()

    permission_classes = [IsAuthenticated]
    filter_class = FilterClass

    def get(self, request) -> Response:
        check_perms(request.user, "billingperiod.view_billingperiod")
        filters = self.validate_filter(data=request.query_params)
        selected = sl.billing_list_for(request.user, filters)
        return get_paginated_response(
            view=self,
            request=request, 
            queryset=selected, 
            serializer_class=sc.BillingListSerializer, 
        )


class BillingDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, billing_id: int) -> Response:
        check_perms(request.user, "billingperiod.view_billingperiod")
        selected = sl.billing_get_for(request.user, billing_id)
        outgoing = sc.BillingDetailSerializer(instance=selected)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class BillingCancelView(BaseAPIView):
    """Allow users to cancel a billing period"""

    permission_classes = [IsAuthenticated]

    def post(self, request, billing_id: int) -> Response:
        check_perms(request.user, "billingperiod.change_billingperiod")
        selected = sl.billing_get_for(request.user, billing_id)
        billing = sr.billing_period_cancel(selected)
        outgoing = sc.BillingDetailSerializer(instance=billing)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class BillingCompleteView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = sc.BillingCompleteSerializer

    def post(self, request, billing_id: int) -> Response:
        check_perms(request.user, "billingperiod.complete_billingperiod")
        billing = sl.billing_get_for(request.user, billing_id)
        incoming = self.validate_serializer(data=request.data)
        payment = incoming["payment"]
        # This ensures explicitness
        if billing != payment.billing:
            raise ValidationError("Payment does not belong to this billing period")
        
        billing = sr.billing_period_complete(**payment)
        outgoing = sc.BillingDetailSerializer(instance=billing)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)

