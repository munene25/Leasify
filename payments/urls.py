from django.urls import path
from payments import views

urlpatterns = [
    # Payment List - List and retrieve all payments accessible by the authenticated user
    path("", views.PaymentListView.as_view(), name="payment_list"),
    # Initiate M-Pesa payment via STK push
    path("mpesa/initiate/<int:billing_id>", views.PaymentInitiateMpesaView.as_view(), name="payment_initiate"),
    # Callback endpoint for M-Pesa to update payment status
    path("mpesa/callback/", views.PaymentMpesaCallbackView.as_view(), name="payment_callback"),
    # Manually create a payment via alternate mode (CASH/BANK)
    path("alt/create/<int:billing_id>", views.PaymentAltCreateView.as_view(), name="payment_alt_create"),
    # Payment detail endpoint - Retrieve specific payment information
    path("<int:payment_id>", views.PaymentDetailView.as_view(), name="payment_detail"),
]
