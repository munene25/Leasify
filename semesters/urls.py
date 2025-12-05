from django.urls import path
from . import views

urlpatterns = [
    path("", views.SemesterListCreateView.as_view(), name="list_create"),
    path("<int:semester_id>/", views.SemesterDetailUpdateDeleteView.as_view(), name="detail_update_delete"),
]
