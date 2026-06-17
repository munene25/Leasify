from django.urls import path
from tenancy import views

urlpatterns = [
    path("", views.TenancyListCreateView.as_view(), name="list_create"),
    path("<int:tenancy_id>", views.TenancyDetailView.as_view(), name="detail_update"),
    path("<int:tenancy_id>/terminate", views.TenancyTerminateView.as_view(), name="detail_update"),
    path("<int:tenancy_id>/extend", views.TenancyLeaseExtensionView.as_view(), name="detail_update"),
    path("termination-reasons", views.TenancyTerminationReasonsView.as_view(), name="termination_reasons"),
]