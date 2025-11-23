from django.urls import path
from . import views

urlpatterns = [
    path("", views.ApartmentListCreateView.as_view(), name="list_create"),
    path("overview", views.ApartmentOverviewView.as_view(), name="overview"),
    path("<int:apartment_id>/", views.ApartmentDetailUpdateView.as_view(), name="detail_update"),
]
