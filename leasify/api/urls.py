from django.urls import path
from leasify.api import views

app_name = "api"

urlpatterns = [
    path("health", views.HealthCheckView.as_view(), name="health")
]