from django.urls import path
from . import views


urlpatterns = [
    path("me", views.MeView.as_view(), name="me"),
    path("", views.UserListCreateView.as_view(), name="user_list_create"),
    path("<int:user_id>", views.AdminUserDetailUpdateDestroyView.as_view(), name="admin_detail"),
    path("<int:user_id>/roles", views.AdminUserRoleDetailView.as_view(), name="admin_role_detail"),
    path("roles", views.AdminUserRoleListView.as_view(), name="admin_role_list"),
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("refresh", views.RefreshSessionView.as_view(), name="refresh"),
    path("password-change", views.PasswordChangeView.as_view(), name="password_change" ),
    path("email-change", views.EmailUpdateView.as_view(), name="email_change" ),
    path("request/password-reset", views.RequestPasswordResetView.as_view(), name="send_password_reset"),
    path("confirm/password-reset/<str:uidb64>/<str:token>", views.ConfirmPasswordResetView.as_view(), name="confirm_password_reset" ),
    path("request/email-verification", views.RequestEmailVerificationView.as_view(), name="send_email_verification" ),
    path("confirm/email-verification/<str:uidb64>/<str:token>", views.ConfirmEmailVerificationView.as_view(), name="confirm_email_verification" ),
    path("unsubscribe/<str:uidb64>", views.UserUnsubscribeView.as_view(), name="unsubscribe")
]
