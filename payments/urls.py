from django.urls import path
from payments import views

urlpatterns = [
    # List and retrieve all payments accessible by the authenticated user
    path("", views.PaymentListView.as_view(), name="payment_list"),
    # Retrieve specific payment information
    path("<int:payment_id>/", views.PaymentDetailView.as_view(), name="payment_detail"),
    # Initiate M-Pesa payment via STK push (billing_id in POST data, supports idempotency key)
    path("mpesa/initiate/", views.PaymentInitiateMpesaView.as_view(), name="payment_initiate_mpesa"),
    # Callback endpoint for M-Pesa to update payment status
    path("mpesa/callback/", views.PaymentMpesaCallbackView.as_view(), name="payment_callback"),
    # Manually create a payment via alternate mode (CASH/BANK) (billing_id in POST data)
    path("alt/", views.PaymentAltCreateView.as_view(), name="payment_alt_create"),
    # Query and update M-PESA payment status
    path("<int:payment_id>/query/", views.PaymentStatusQueryView.as_view(), name="payment_query_status"),
]
