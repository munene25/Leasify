from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from common.pagination import get_paginated_response
from common.permissions import check_perms
from payments import services as sr, selectors as sl, serializer as sc
from common.views import BaseAPIView
from payments.mpesa import parse_response


class PaymentListView(BaseAPIView):
    """List and retrieve all payments accessible by the authenticated user."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = sc.PaymentListSerializer
    
    class FilterClass(serializers.Serializer):
        billing = serializers.IntegerField()
        status = serializers.CharField()
        payment_mode = serializers.CharField()
        search = serializers.CharField()

    def get(self, request) -> Response:
        check_perms(request.user, "payment.view_payment")
        filters = self.validate_filter(data=request.query_params)
        payments_qs = sl.payment_list_for(user=request.user, filters=filters)

        return get_paginated_response(
            serializer_class=sc.PaymentListSerializer,
            queryset=payments_qs,
            request=request,
            view=self,
        )


class PaymentInitiateMpesaView(BaseAPIView):
    """Initiate an M-Pesa payment via STK push"""

    permission_classes = [IsAuthenticated]
    serializer_class = sc.PaymentInitiateMpesaSerializer

    def post(self, request) -> Response:
        incoming = self.validate_serializer(data=request.data)
        payment = sr.payment_mpesa_initiate(**incoming)
        return Response(data={"message": "An M-Pesa transaction has been initiated.", "payment_id": payment.pk})


class PaymentDetailView(APIView):
    """Retrieve detailed information about a specific payment."""

    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id: int) -> Response:
        check_perms(request.user, "payment.view_payment")
        selected = sl.payment_get_for(user=request.user, payment_id=payment_id)
        outgoing = sc.PaymentDetailSerializer(instance=selected)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class PaymentMpesaCallbackView(BaseAPIView):
    """Update payment status based on callback response."""

    def post(self, request) -> Response:
        cb = parse_response(request.data)
        payment = sr.payment_mpesa_confirm(cb=cb)
        outgoing = sc.PaymentDetailSerializer(instance=payment)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class PaymentAltCreateView(BaseAPIView):
    """Manually create a payment via alternate mode (CASH/BANK)."""

    permission_classes = [IsAuthenticated]
    serializer_class = sc.PaymentAltCreateSerializer

    def post(self, request) -> Response:
        check_perms(request.user, "add_payment_manually")
        incoming = self.validate_serializer(data=request.data)
        payment = sr.payment_alt_create(**incoming)
        outgoing = sc.PaymentDetailSerializer(instance=payment)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)
