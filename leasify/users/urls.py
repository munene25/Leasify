from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("me", views.MeView.as_view(), name="me"),
    path("", views.UserListCreateView.as_view(), name="user_list_create"),
    path("<int:user_id>", views.AdminDetailUpdateDestroyView.as_view(), name="admin_detail"),
    path("roles/<int:user_id>", views.AdminRoleDetailView.as_view(), name="admin_role_detail"),
    path("roles", views.AdminRoleListView.as_view(), name="admin_roles_list"),
    path("email-change", views.EmailUpdateView.as_view(), name="email_change" ),
    path("unsubscribe/<str:uidb64>", views.UserUnsubscribeView.as_view(), name="unsubscribe")
]
