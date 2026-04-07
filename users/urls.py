from django.urls import path
from . import views


urlpatterns = [
    path("me", views.MeView.as_view(), name="me"),
    path("", views.UserListCreateView.as_view(), name="user_list_create"),
    path("<int:user_id>", views.AdminUserDetailUpdateDestroyView.as_view(), name="admin_detail"),
    path("roles/<int:user_id>", views.AdminUserRoleDetailView.as_view(), name="admin_role_detail"),
    path("roles", views.AdminUserRoleListView.as_view(), name="admin_roles_list"),
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("refresh", views.RefreshSessionView.as_view(), name="refresh"),
    path("password-change", views.PasswordChangeView.as_view(), name="password_change" ),
    path("email-change", views.EmailUpdateView.as_view(), name="email_change" ),
    path("password-reset/request", views.RequestPasswordResetView.as_view(), name="send_password_reset"),
    path("password-reset/confirm/<str:uidb64>/<str:token>", views.ConfirmPasswordResetView.as_view(), name="confirm_password_reset" ),
    path("email-verification/request", views.RequestEmailVerificationView.as_view(), name="send_email_verification" ),
    path("email-verification/confirm/<str:uidb64>/<str:token>", views.ConfirmEmailVerificationView.as_view(), name="confirm_email_verification" ),
    path("unsubscribe/<str:uidb64>", views.UserUnsubscribeView.as_view(), name="unsubscribe")
]
