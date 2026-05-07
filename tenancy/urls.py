from django.urls import path
from tenancy import views

urlpatterns = [
    path("", views.TenancyListCreateView.as_view(), name="list_create"),
    path("<int:tenancy_id>", views.TenancyDetailUpdateDestroyView.as_view(), name="detail_update")
]