from django.urls import path
from billing import views

urlpatterns = [
    path("", views.BillingListView.as_view(), name="billing_list"),
    path("<int:billing_id>", views.BillingDetailView.as_view(), name="billing_detail"),
    path("<int:billing_id>/cancel", views.BillingCancelView.as_view(), name="billing_detail"),
    path("<int:billing_id>complete", views.BillingCompleteView.as_view(), name="billing_complete"),
]