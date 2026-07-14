from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotAcceptable
from common.pagination import get_paginated_response
from common.permissions import check_perms
from payments import services as sr, selectors as sl, serializer as sc, models as md
from common.views import BaseAPIView
from payments.mpesa import parse_callback_response
from payments import tasks
from billing.selectors import billing_get_for


class PaymentListView(BaseAPIView):
    """List and retrieve all payments accessible by the authenticated user.

    Filters available: billing_id, status, mode, search query string.

    :param request: The HTTP request containing authentication token and optional query parameters
    :returns: Paginated list of Payment objects with filtering applied
    """

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


class PaymentInitiateMpesaView(BaseAPIView):
    """Initiate an M-Pesa payment via STK push.

    Initiates a new payment using the M-PESA mobile money service with STK push notification.
    The user will be prompted to enter their PIN on their device.

    :param request: The HTTP POST request containing billing_id and phone_number in body
    :returns: Response with payment ID upon successful initiation (201 CREATED)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = sc.PaymentInitiateMpesaSerializer

    def post(self, request) -> Response:
        
        idempotency_key = request.headers.get("Idempotency-Key", None)
        
        incoming = self.validate_serializer(data=request.data)
        billing = billing_get_for(user=request.user, billing_id=incoming["billing_id"])

        payment = sr.payment_mpesa_initiate(
            billing=billing, phone_number=incoming["phone_number"], idempotency_key=idempotency_key
        )

        return Response(
            {"message": "M-Pesa transaction initiated.", "payment_id": payment.pk},
            status=status.HTTP_201_CREATED,
        )


class PaymentDetailView(APIView):
    """Retrieve detailed information about a specific payment.

    Retrieves full details of a single payment record accessible by the authenticated user.

    :param request: The HTTP GET request containing authentication token and payment_id in path
    :param payment_id: The unique identifier of the payment to retrieve (int)
    :returns: Response with Payment object serialized data (200 OK)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id: int) -> Response:
        check_perms(request.user, "payment.view_payment")
        selected = sl.payment_get_for(user=request.user, payment_id=payment_id)
        outgoing = sc.PaymentDetailSerializer(instance=selected)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class PaymentStatusQueryView(BaseAPIView):
    """
    Query and update the status of an M-PESA payment.

    Queries the current status of an M-PESA transaction via the MPESA endpoint and updates the internal payment record accordingly.

    :param request: The HTTP POST request containing authentication token and payment_id in path
    :param payment_id: The unique identifier of the payment to query (int)
    :returns: Response with updated Payment object serialized data (200 OK)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id: int) -> Response:
        check_perms(request.user, "payment.view_payment")

        # Get the payment for the user to verify access (raises if not found)
        selected = sl.payment_get_for(user=request.user, payment_id=payment_id)
        payment = sr.payment_mpesa_query(selected)
        outgoing = sc.PaymentDetailSerializer(instance=payment)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class PaymentMpesaCallbackView(BaseAPIView):
    """
    Update payment status based on callback response.

    Processes an M-PESA STK push callback and updates the internal payment record with transaction result.

    :param request: The HTTP POST request containing the MPESA callback JSON data
    :returns: Response indicating successful processing (200 OK)
    """

    def post(self, request) -> Response:
        stk_result = parse_callback_response(request.data)
        tasks.payment_mpesa_process_async.delay(stk_result)
        return Response(status=status.HTTP_200_OK)


class PaymentAltCreateView(BaseAPIView):
    """
    Manually create a payment via alternate mode (CASH/BANK).

    Creates a payment manually through CASH or BANK modes, bypassing the M-PESA STK push flow.

    :param request: The HTTP POST request containing authentication token and payment data in body
    :returns: Response with Payment object serialized data (201 CREATED)
    """

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
