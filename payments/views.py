from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotAcceptable
from django.core.cache import cache
from common.pagination import get_paginated_response
from common.permissions import check_perms
from payments import services as sr, selectors as sl, serializer as sc
from common.views import BaseAPIView
from payments.mpesa import parse_callback_response
from payments.choices import PaymentStatus as PS
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

    def post(self, request) -> Response:

        # Raise error if no idemp key is in header
        try: idem_key = request.headers["Idempotency-Key"]
        except KeyError: raise NotAcceptable("'Idempotency-Key' header missing")
        cache_key = f"payments:mpesa:idemp:{idem_key}"

        # Try to set cache immediately to minimize concurency exposure
        if not cache.add(cache_key, None, timeout=300):
            cached = cache.get(cache_key)
            message = {"message":"An M-Pesa transaction is already underway."}
            message.update({"payment_id": cached}) if cached is not None else {}
            return Response(data=message, status=200)
        
        incoming = self.validate_serializer(data=request.data)
        billing = billing_get_for(user=request.user, billing_id=incoming["billing_id"])

        # Service checks for pending payments or if billing status is paid
        payment = sr.payment_mpesa_initiate(billing=billing, phone_number=incoming["phone_number"])
        
        # Set cache with correct payment_id
        cache.set(cache_key, payment.pk, timeout=300)
            
        return Response(
            data={
                "message": "An M-Pesa transaction has been initiated.", 
                "payment_id": payment.pk
            },
            status=status.HTTP_201_CREATED,
        )
    


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
        payment = sr.payment_mpesa_query(selected)
        outgoing = sc.PaymentDetailSerializer(instance=payment)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


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

    def post(self, request) -> Response:
        check_perms(request.user, "add_payment_manually")
        incoming = self.validate_serializer(data=request.data)
        billing_id = incoming.pop("billing_id")
        billing = billing_get_for(request.user, billing_id=billing_id)
        payment = sr.payment_alt_create(billing=billing, **incoming)
        outgoing = sc.PaymentDetailSerializer(instance=payment)
        return Response(data=outgoing.data, status=status.HTTP_201_CREATED)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)
