from django.urls import path
from leasify.authentication import views

app_name = "authentication"


urlpatterns = [
    path("csrf", views.CsrfView.as_view(), name="csrf"),
    path("login", views.LoginView.as_view(), name="login"),
    path("google/login", views.GoogleLoginView.as_view(), name="google_login"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("refresh", views.RefreshSessionView.as_view(), name="refresh"),
    path("password-change", views.PasswordChangeView.as_view(), name="password_change"),
    path("password-reset/request", views.RequestPasswordResetView.as_view(), name="send_password_reset"),
    path("password-reset/confirm/<str:uidb64>/<str:token>", views.ConfirmPasswordResetView.as_view(), name="confirm_password_reset"),
    path("email-verification/request", views.RequestEmailVerificationView.as_view(), name="send_email_verification" ),
    path("email-verification/confirm/<str:uidb64>/<str:token>", views.ConfirmEmailVerificationView.as_view(), name="confirm_email_verification"),
]