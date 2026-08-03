from structlog import get_logger

from django.contrib import auth
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from leasify.common.views import BaseAPIView
from leasify.common.throttling import EmailThrottle

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
    throttle_classes = [EmailThrottle]
    throttle_scope = "failed_login_attempts"

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)
        user = sr.user_authenticate(**incoming)
        # initialize the session
        auth.login(request, user=user)
        return Response(data={"message": "Login successful"}, status=status.HTTP_200_OK)


class LogoutView(BaseAPIView):
    """
    Flush current user session and delete session_id cookie
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.user.pk
        auth.logout(request)
        logger.info("user_logged_out", target_id=user_id)
        return Response(data={"message": "Logout successful"}, status=status.HTTP_200_OK)


class RefreshSessionView(BaseAPIView):
    """
    A means to extend the expiry time for authenticated users.
    Frontend ideally, should periodically hit this endpoint.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.conf import settings
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        return Response({"message": "Session extended"})


class PasswordChangeView(BaseAPIView):
    """View orchestrates password change for logged in user. Throttles based on user.email"""

    permission_classes = [IsAuthenticated]
    serializer_class = sc.PasswordChangeSerializer
    throttle_classes = [EmailThrottle]
    throttle_scope = "password_changes"

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)
        user = sr.user_change_password(user=request.user, **incoming)
        auth.update_session_auth_hash(request, user)

        return Response(data={"message": "Password change successful"}, status=status.HTTP_200_OK)


class RequestPasswordResetView(BaseAPIView):
    """
    Forgot password route.
    Payload includes the registered email address.
    Returns a consistent response for both registered and unregistered users
    Throttles based on email in request body.
    Logs reflect which email is requesting the password reset
    """

    permission_classes = [AllowAny]
    serializer_class = sc.RequestPasswordResetSerializer
    throttle_classes = [EmailThrottle]
    throttle_scope = "password_resets"

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)

        try: user = user_get_by_email(incoming["email"])
        except NotFound: pass

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
            data={"message": "Password has been reset successfully"},
            status=status.HTTP_200_OK,
        )

class RequestEmailVerificationView(BaseAPIView):
    """
    View sends an email to the requesting user to verify email.
    The link points to the fronted with then posts to this view.
    Done via post as it's an unsafe operation.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [EmailThrottle]
    serializer_class = sc.RequestEmailVerificationSerializer
    throttle_scope = "email_verifications"

    def post(self, request):
        user = request.user
        incomming = self.validate_serializer(data=request.data)

        if not user.verified:
            ts.send_token_email.delay(
                user_id=user.pk,
                url_path=incomming["url_path"],
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



class CsrfView(BaseAPIView):
    """Set the CSRF cookie."""

    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"message": "csrf set"})