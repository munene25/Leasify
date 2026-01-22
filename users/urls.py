from django.urls import path
from . import views


urlpatterns = [
    path("me", views.MeView.as_view(), name="me"),
    path("", views.UserListCreateView.as_view(), name="users_list_create"),
    path("<int:user_id>", views.UserDetailUpdateDestroyView.as_view(), name="users_detail_update_destroy"),
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("refresh-token/", views.RefreshTokenView.as_view(), name="refresh_token"),
    path("password-change", views.PasswordChangeView.as_view(), name="users_password_change" ),
    path("request/password-reset", views.RequestPasswordResetView.as_view(), name="send_password_reset"),
    path("request/email-verification", views.RequestEmailVerificationView.as_view(), name="send_email_verification" ),
    path("confirm/email-verification/<str:uuid>/<str:token>", views.ConfirmEmailVerificationView.as_view(), name="verify_email" ),
    path("confirm/password_reset/<str:uuid>/<str:token>", views.ConfirmPasswordResetView.as_view(), name="verify_password" ),
    path("unsubscribe/<str:uuid>", views.UserUnsubscribeView.as_view(), name="unsubscribe")
]
