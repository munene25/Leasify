from django.urls import path
from payments import views

urlpatterns = [
    # Payment List - List and retrieve all payments accessible by the authenticated user
    path("list/", views.PaymentListView.as_view(), name="payment_list"),
    # Initiate M-Pesa payment via STK push
    path("initiate/", views.PaymentInitiateMpesaView.as_view(), name="payment_initiate"),
    # Callback endpoint for M-Pesa to update payment status
    path("mpesa/callback/", views.PaymentMpesaCallbackView.as_view(), name="payment_callback"),
    # Manually create a payment via alternate mode (CASH/BANK)
    path("alt/create/", views.PaymentAltCreateView.as_view(), name="payment_alt_create"),
]
