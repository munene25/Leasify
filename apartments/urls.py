from django.urls import path
from apartments import views

urlpatterns = [
    path("", views.ApartmentListCreateView.as_view(), name="list_create"),
    path("<int:apartment_id>", views.ApartmentDetailUpdateDeleteView.as_view(), name="detail_update_delete"),
    path("choices", views.ApartmentChoicesView.as_view(), name="choices"),
]
