from django.urls import path
from tenancy import views

app_name = "tenancy"

urlpatterns = [
    path("", views.TenancyListCreateView.as_view(), name="list_create"),
    path("<int:tenancy_id>", views.TenancyDetailView.as_view(), name="detail_update"),
    path("<int:tenancy_id>/terminate", views.TenancyTerminateView.as_view(), name="terminate"),
    path("<int:tenancy_id>/extend", views.TenancyLeaseExtensionView.as_view(), name="lease_extend"),
    path("choices", views.TenancyChoicesViews.as_view(), name="choices"),
]