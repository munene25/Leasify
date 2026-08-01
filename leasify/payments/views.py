from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from leasify.common.views import BaseAPIView

from leasify.common.pagination import get_paginated_response
from leasify.common.permissions import check_perms
from leasify.billing import selectors as billing_sl

from leasify.payments import models as md, selectors as sl, serializer as sc
from leasify.payments import tasks
from leasify.payments.mpesa import parse_callback_response
from leasify.payments import services as sr


class PaymentListView(BaseAPIView):
    """List and retrieve payments accessible by the user."""

    class FilterClass(serializers.Serializer):
        billing = serializers.IntegerField()
        status = serializers.CharField()
        mode = serializers.CharField()
        search = serializers.CharField()

    permission_classes = [IsAuthenticated]
    serializer_class = sc.PaymentListSerializer
    filter_class = FilterClass

    def get(self, request) -> Response:
        check_perms(request.user, "payments.view_payment")
        filters = self.validate_filter(data=request.query_params)
        payments_qs = sl.payment_list_for(user=request.user, filters=filters)

        return get_paginated_response(
            serializer_class=sc.PaymentListSerializer,
            queryset=payments_qs,
            request=request,
            view=self,
        )


class PaymentDetailView(APIView):
    """Retrieve details about a specific payment."""

    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id: int) -> Response:
        check_perms(request.user, "payments.view_payment")
        selected = sl.payment_get_for(user=request.user, payment_id=payment_id)
        outgoing = sc.PaymentDetailSerializer(instance=selected)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class PaymentInitiateMpesaView(BaseAPIView):
    """Initiates an M-Pesa payment via STK push."""

    # ? Need to add throttle class?

    permission_classes = [IsAuthenticated]
    serializer_class = sc.PaymentInitiateMpesaSerializer

    def post(self, request) -> Response:
        check_perms(request.user, "payments.initiate_payment")
        idempotency_key = request.headers.get("Idempotency-Key", None)

        incoming = self.validate_serializer(data=request.data)
        # Billing needs to be obtained via selector to filter viewable billings.
        billing = billing_sl.billing_get_for(user=request.user, billing_id=incoming["billing_id"])


        payment = sr.payment_mpesa_initiate(
            billing=billing,
            phone_number=incoming["phone_number"], 
            idempotency_key=idempotency_key,
            callback_url = request.build_absolute_uri(reverse("payments:mpesa_callback"))
        )

        return Response(
            {"message": "M-Pesa transaction initiated.", "payment_id": payment.pk, "status": payment.status},
            status=status.HTTP_201_CREATED,
        )


class PaymentStatusQueryView(BaseAPIView):
    """Queries the status of an M-PESA payment."""

    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id: int) -> Response:
        check_perms(request.user, "payments.view_payment")

        # Get the payment for the user to verify access (raises if not found)
        selected = sl.payment_get_for(user=request.user, payment_id=payment_id)
        result = sr.payment_mpesa_query(selected)
        tasks.payment_mpesa_process_async.delay(result)
        return Response(
            data={"message": "Payment query in progress", "payment_id": selected.pk, "status": selected.status},
            status=status.HTTP_200_OK,
        )


class PaymentMpesaCallbackView(BaseAPIView):
    """Processes an M-PESA STK push callback."""

    @csrf_exempt
    def post(self, request) -> Response:
        # IP filtering done in reverse proxy
        stk_result = parse_callback_response(request.data)
        tasks.payment_mpesa_process_async.delay(stk_result)
        return Response(status=status.HTTP_200_OK)


class PaymentAltCreateView(BaseAPIView):
    """Creates payments manually via alternative modes."""

    permission_classes = [IsAuthenticated]
    serializer_class = sc.PaymentAltCreateSerializer

    def post(self, request) -> Response:
        check_perms(request.user, "payments.add_payment_manually")
        incoming = self.validate_serializer(data=request.data)
        billing_id = incoming.pop("billing_id")
        billing = billing_sl.billing_get_for(user=request.user, billing_id=billing_id)
        payment = sr.payment_alt_create(billing=billing, recorded_by=request.user, **incoming)
        outgoing = sc.PaymentDetailSerializer(instance=payment)
        return Response(data=outgoing.data, status=status.HTTP_201_CREATED)
