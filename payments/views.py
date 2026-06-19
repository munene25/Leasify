from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from common.pagination import get_paginated_response
from common.permissions import check_perms
from payments import services as sr, selectors as sl, serializer as sc
from common.views import BaseAPIView
from payments.mpesa import parse_callback_response, query_payment_status
from billing.selectors import billing_get_for

class PaymentListView(BaseAPIView):
    """List and retrieve all payments accessible by the authenticated user."""

    class FilterClass(serializers.Serializer):
        billing = serializers.IntegerField()
        status = serializers.CharField()
        payment_mode = serializers.CharField()
        search = serializers.CharField()

    permission_classes = [IsAuthenticated]
    serializer_class = sc.PaymentListSerializer
    filter_class = FilterClass

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

    def post(self, request, billing_id: int) -> Response:
        # Get billing through selector to ensure the user can even see the billing
        # ? Filter out paid billing?
        billing = billing_get_for(user=request.user, billing_id=billing_id)
        incoming = self.validate_serializer(data=request.data)
        payment = sr.payment_mpesa_initiate(billing=billing, phone_number=incoming["phone_number"])
        return Response(data={"message": "An M-Pesa transaction has been initiated.", "payment_id": payment.pk})


class PaymentDetailView(APIView):
    """Retrieve detailed information about a specific payment."""

    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id: int) -> Response:
        check_perms(request.user, "payment.view_payment")
        selected = sl.payment_get_for(user=request.user, payment_id=payment_id)
        outgoing = sc.PaymentDetailSerializer(instance=selected)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class PaymentStatusQueryView(BaseAPIView):
    """Query and update the status of an M-PESA payment."""

    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id: int) -> Response:
        check_perms(request.user, "payment.view_payment")

        # Get the payment for the user to verify access (raises if not found)
        selected = sl.payment_get_for(user=request.user, payment_id=payment_id)

        # All checkout_ids are M-PESA payments, so we can query directly
        if not selected.checkout_id:
            raise ValidationError("Only MPESA payments can be queried")

        try: stk_result = query_payment_status(selected.checkout_id)
        except: raise ValidationError("Could not complete the request at this time")
        # Update the payment status based on the result
        payment = sr.payment_mpesa_process(stk_result)

        # Return updated payment details
        outgoing = sc.PaymentDetailSerializer(instance=payment)
        return Response(data={"result_desc": f"{stk_result.result_desc}",}.update(outgoing.data), status=status.HTTP_200_OK)


class PaymentMpesaCallbackView(BaseAPIView):
    """Update payment status based on callback response."""

    def post(self, request) -> Response:
        stk_result = parse_callback_response(request.data)
        sr.payment_mpesa_process(stk_result)
        return Response(status=status.HTTP_200_OK)


class PaymentAltCreateView(BaseAPIView):
    """Manually create a payment via alternate mode (CASH/BANK)."""

    permission_classes = [IsAuthenticated]
    serializer_class = sc.PaymentAltCreateSerializer

    def post(self, request, billing_id: int) -> Response:
        check_perms(request.user, "add_payment_manually")
        incoming = self.validate_serializer(data=request.data)
        billing = billing_get_for(request.user, billing_id=billing_id)
        payment = sr.payment_alt_create(billing=billing, **incoming)
        outgoing = sc.PaymentDetailSerializer(instance=payment)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)
