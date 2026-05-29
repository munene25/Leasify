from django.urls import path
from tenancy import views

urlpatterns = [
    path("", views.TenancyListCreateView.as_view(), name="list_create"),
    path("<int:tenancy_id>", views.TenancyDetailUpdateView.as_view(), name="detail_update"),
    path("terminate/<int:tenancy_id>", views.TenancyTerminateView.as_view(), name="tenancy_terminate"),
]