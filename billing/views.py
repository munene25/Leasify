from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status
from common.pagination import get_paginated_response
from common.permissions import check_perms
from billing import serializer as sc, services as sr, selectors as sl
from billing.choices import BillingStatus


from common.views import BaseAPIView
class BillingListView(BaseAPIView):
    """List billing periods for the authenticated user.
    
    Retrieves a paginated list of billing periods accessible by the current user,
    with optional filtering based on date range and other criteria.
    """

    class FilterClass(serializers.Serializer):
        period_after = serializers.DateField()
        period_before = serializers.DateField()
        is_current = serializers.BooleanField(allow_null=True)
        search = serializers.CharField()

    permission_classes = [IsAuthenticated]
    filter_class = FilterClass

    def get(self, request) -> Response:
        check_perms(request.user, "billing.view_billingperiod")
        filters = self.validate_filter(data=request.query_params)
        selected = sl.billing_list_for(user=request.user, filters=filters)
        return get_paginated_response(
            view=self,
            request=request,
            queryset=selected,
            serializer_class=sc.BillingListSerializer,
        )


class BillingDetailView(BaseAPIView):
    """Retrieve detailed information about a specific billing period.
    
    Returns full details of a billing period including payment status,
    amount, and associated information accessible to the user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, billing_id: int) -> Response:
        check_perms(request.user, "billing.view_billingperiod")
        selected = sl.billing_get_for(user=request.user, billing_id=billing_id)
        outgoing = sc.BillingDetailSerializer(instance=selected)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class BillingCancelView(BaseAPIView):
    """Cancel an existing billing period.
    
    Allows authenticated users to cancel their current active billing period,
    returning the updated billing information after cancellation.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, billing_id: int) -> Response:
        check_perms(request.user, "billing.change_billingperiod")
        selected = sl.billing_get_for(user=request.user, billing_id=billing_id)
        billing = sr.billing_period_cancel(selected)
        outgoing = sc.BillingDetailSerializer(instance=billing)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class BillingCompleteView(BaseAPIView):
    """Complete and finalize a billing period payment.
    
    Processes payment completion for an unpaid billing period, validates the 
    current status before processing, and returns updated billing information.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, billing_id: int) -> Response:
        check_perms(request.user, "billing.complete_billingperiod")
        selected = sl.billing_get_for(user=request.user, billing_id=billing_id)
        
        # Check if billing is already paid or cancelled
        if selected.status != BillingStatus.UNPAID:
            raise ValidationError(f"Billing period is already {selected.status}")
        
        billing = sr.billing_period_complete(selected)
        outgoing = sc.BillingDetailSerializer(instance=billing)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)