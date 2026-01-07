from django.urls import path
from . import views


urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("signup/", views.SignUpView.as_view(), name="sign_up"),
    path("refresh-token/", views.RefreshTokenView.as_view(), name="refresh_token"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("edit-profile/", views.UpdateUserProfile.as_view(), name="edit_profile"),
    path(
        "change-password/",
        views.PasswordChangeView.as_view(),
        name="change_password",
    ),
    path("change-email/", views.EmailChangeView.as_view(), name="change_email"),
    path(
        "generate/password-reset/",
        views.SendPasswordResetLinkView.as_view(),
        name="send_password_reset",
    ),
    path(
        "generate/email-verification/",
        views.SendEmailVerificationLinkView.as_view(),
        name="send_email_verification",
    ),
    path(
        "confirm/email-token/<str:uidb64>/<str:token>/",
        views.VerifyEmailTokenView.as_view(),
        name="verify_email",
    ),
    path(
        "confirm/password-token/<str:uidb64>/<str:token>/",
        views.VerifyPasswordTokenView.as_view(),
        name="verify_password",
    ),
    path(
        "me/",
        views.GetUserData.as_view(),
        name="me",
    ),
]
