from structlog import get_logger

from django.contrib.auth import login, logout, update_session_auth_hash

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status

from leasify.common.views import BaseAPIView
from leasify.common.throttling import EmailScopedThrottle

from leasify.authentication import services as sr, serializer as sc, tasks as ts
from leasify.authentication.tokens import token_validate, get_user_from_uidb64
from leasify.users.selectors import user_get_by_email

logger = get_logger("authentication.views")


class LoginView(BaseAPIView):
    """
    Grant the user a session if authentication passes, otherwise raise 401
    Throttles based on failed attempts, Successful request do not count as attempts.
    """

    from config.settings.auth import ForceCSRFAuthentication

    authentication_classes = [ForceCSRFAuthentication]
    permission_classes = [AllowAny]
    serializer_class = sc.LoginSerializer
    throttle_classes = [EmailScopedThrottle]
    throttle_scope = "failed_login_attempts"

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)
        user = sr.user_authenticate(**incoming)
        # initialize the session
        login(request, user=user)

        # On login success, remove the attempt from history
        self.pop_latest_cache_entry(request)
        return Response(data={"message": "login successful"}, status=status.HTTP_200_OK)


class LogoutView(BaseAPIView):
    """
    Flush current user session and delete session_id cookie
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # First store the id to log later
        user_id = request.user.pk
        logout(request)
        logger.info("user_logged_out", target_id=user_id)
        return Response(data={"message": "You have been logged out"}, status=status.HTTP_200_OK)


class RefreshSessionView(BaseAPIView):
    """
    A means to extend the expiry time for authenticated users.
    Frontend ideally, should periodically hit this endpoint.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.session.set_expiry(None)
        return Response({"message": "Session extended"})


class PasswordChangeView(BaseAPIView):
    """
    View orchestrates password change for logged in user.
    Requires two passwords to match and the current password to be correct
    Throttles based on user.email
    """

    permission_classes = [IsAuthenticated]
    serializer_class = sc.PasswordChangeSerializer
    throttle_classes = [EmailScopedThrottle]
    throttle_scope = "password_changes"

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)
        user = sr.user_change_password(user=request.user, **incoming)
        update_session_auth_hash(request, user)

        # Allow rightful user to update password as many times as they want
        self.pop_latest_cache_entry(request)

        return Response(data={"message": "Password has been successfully updated"}, status=status.HTTP_200_OK)


class RequestEmailVerificationView(BaseAPIView):
    """
    View sends an email to the requesting user to verify email.
    The link points to the fronted with then posts to this view.
    Done via post as it's an unsafe operation.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [EmailScopedThrottle]
    throttle_scope = "email_verifications"

    def post(self, request):
        user = request.user
        incomming = self.validate_serializer(data=request.data)

        if not user.verified:
            ts.send_token_email.delay(
                user_id=user.pk,
                url_path=incomming["email-verify"],
                subject="Verify your email address.",
                action_cta="Verify Email",
            )
            logger.info("email_verification_request_sent", target_id=user.pk)
        return Response(
            data={"message": "email verification link sent if user exists"}, status=status.HTTP_202_ACCEPTED
        )


class ConfirmEmailVerificationView(BaseAPIView):
    """
    Allows users to verify their emails
    Skips verification if user is already verified.
    """

    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        user = get_user_from_uidb64(uidb64)
        if not user.verified:
            token_validate(user=user, token=token)
            sr.user_email_verify(user)
        return Response(data={"message": "email has been verified successfully"}, status=status.HTTP_200_OK)


class RequestPasswordResetView(BaseAPIView):
    """
    Forgot password route.
    Payload includes the registered email address.
    Returns a consistent response for both registered and unregistered users
    Throttles based on email.
    Logs reflect which email is requesting the password reset
    """

    permission_classes = [AllowAny]
    serializer_class = sc.RequestPasswordResetSerializer
    throttle_classes = [EmailScopedThrottle]
    throttle_scope = "password_resets"

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)
        try:
            user = user_get_by_email(incoming["email"])
        except NotFound:
            pass
        else:
            ts.send_token_email.delay(
                user_id=user.pk,
                url_path=incoming["url_path"],
                subject="Reset your password",
                action_cta="Reset password",
            )
            logger.info("password_reset_request_sent", target_id=user.pk)
        return Response(data={"message": "password reset link sent if user exists"}, status=status.HTTP_202_ACCEPTED)


class ConfirmPasswordResetView(BaseAPIView):
    """
    Allows password reset after user follows link sent via the recovery method.
    """

    permission_classes = [AllowAny]
    serializer_class = sc.ConfirmPasswordResetSerializer

    def post(self, request, uidb64, token):
        user = get_user_from_uidb64(uidb64)
        token_validate(user=user, token=token)
        incoming = self.validate_serializer(data=request.data)
        sr.user_change_password(user=user, is_ressetting=True, **incoming)
        return Response(
            data={"message": "password has been reset successfully"},
            status=status.HTTP_200_OK,
        )
