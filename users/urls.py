from django.urls import path
from . import views


urlpatterns = [
    path("me", views.MeView.as_view(), name="me"),
    path("", views.UserListCreateView.as_view(), name="users_list_create"),
    path("<int:user_id>", views.AdminUserDetailUpdateDestroyView.as_view(), name="users_detail"),
    path("<int:user_id>/roles", views.UserRoleDetailView.as_view(), name="roles_detail"),
    path("roles", views.UserRoleListView.as_view(), name="roles_list"),
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("refresh", views.RefreshSessionView.as_view(), name="refresh"),
    path("password-change", views.PasswordChangeView.as_view(), name="users_password_change" ),
    path("email-change", views.EmailUpdateView.as_view(), name="email_update_view" ),
    path("request/password-reset", views.RequestPasswordResetView.as_view(), name="send_password_reset"),
    path("confirm/password-reset/<str:uuid>/<str:token>", views.ConfirmPasswordResetView.as_view(), name="confirm_password_reset" ),
    path("request/email-verification", views.RequestEmailVerificationView.as_view(), name="send_email_verification" ),
    path("confirm/email-verification/<str:uuid>/<str:token>", views.ConfirmEmailVerificationView.as_view(), name="confirm_email_verification" ),
    path("unsubscribe/<str:uuid>", views.UserUnsubscribeView.as_view(), name="unsubscribe")
]
