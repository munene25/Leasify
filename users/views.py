from structlog import getLogger
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework import status
from common.views import BaseAPIView
from common.permissions import check_perms
from django.contrib.auth import login, logout, update_session_auth_hash
from common.pagination import get_paginated_response
from common.throttling import (
    AnonSustained,
    EmailScopedThrottle,
)
from users.tokens import build_user_url, token_validate, get_user_from_uidb64
from users.tasks import send_token_email
from users.services import (
    user_account_create,
    user_add_role,
    user_authenticate,
    user_update,
    user_email_update,
    user_email_verify,
    user_change_password,
    user_deactivate,
    user_remove_role,
    account_unsubscribe,
)
from users.selectors import (
    user_list_for,
    user_get_for,
    user_get,
    user_get_by_email,
    groups_list,
)
from users import serializer as sc

logger = getLogger("users.views")


class UserListCreateView(BaseAPIView):
    """
    Serves as an admin's user-list view via get and new user registration via post
    Permission class is determined via method
    Filtering is allowed via 'search' and 'is_active'

    """

    class FilterSerializer(serializers.Serializer):
        search = serializers.CharField()
        is_active = serializers.BooleanField(allow_null=True)

    serializer_class = sc.UserCreateSerializer
    throttle_classes = [AnonSustained]
    filter_class = FilterSerializer

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "GET" else [AllowAny()]

    def get(self, request: Request):
        check_perms(request.user, "users.view_user")
        filters = self.validate_filter(data=request.query_params)
        qs = user_list_for(user=request.user, filters=filters)
        return get_paginated_response(s_cls=sc.UserListSerializer, qs=qs, req=request, view=self)

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)
        user = user_account_create(**incoming)
        return Response(data={"message": "account has been created"}, status=status.HTTP_201_CREATED)


class AdminUserDetailUpdateDestroyView(BaseAPIView):
    """
    Allows Admins or Authroized groups to modify users details
    All methods require priviledged access
    Selectors with _for should be used
    """

    serializer_class = sc.AdminUserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        check_perms(request.user, "users.view_user")
        user = user_get_for(user=request.user, user_id=user_id)
        serialzer_class = sc.AdminUserDetailSerializer(instance=user)
        return Response(status=status.HTTP_200_OK, data=serialzer_class.data)

    def patch(self, request, user_id):
        check_perms(request.user, "users.change_user")
        incoming = self.validate_serializer(data=request.data, partial=True)
        user = user_get_for(user=request.user, user_id=user_id)
        mod = user_update(user, **incoming)

        outgoing = sc.AdminUserDetailSerializer(instance=mod)
        logger.info(f"Admin modified user data.", target_id=user_id)

        return Response(data=outgoing.data, status=status.HTTP_200_OK)

    def delete(self, request, user_id):
        check_perms(request.user, "users.delete_user")
        user = user_get_for(user=request.user, user_id=user_id)
        user_deactivate(user=user)
        logger.info(f"Admin deactivated user.", target_id=user_id)
        return Response(
            status=status.HTTP_200_OK,
            data={"message": f"{user.full_name}'s account deactivated successfully"},
        )


class MeView(BaseAPIView):
    """
    Provides endpoints for users to manage their own account
    """

    serializer_class = sc.UserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = user_get(request.user.pk)
        outgoing = sc.UserDetailSerializer(instance=user)
        return Response(status=status.HTTP_200_OK, data=outgoing.data)

    def patch(self, request):
        incoming = self.validate_serializer(data=request.data, partial=True)
        user = user_update(user=request.user, **incoming)

        outgoing = sc.UserDetailSerializer(instance=user)
        logger.info(f"User modified self.")
        return Response(data=outgoing.data, status=status.HTTP_200_OK)

    def delete(self, request):
        user_deactivate(user=request.user)

        logger.info(f"User deactivated self.")
        # flush the session
        # Fixed bug: Logout requires the request object not request.user
        logout(request)
        return Response(data={"message": "account deactivated successfully"}, status=status.HTTP_204_NO_CONTENT)


class LoginView(BaseAPIView):
    """
    Grant the user a session if authentication passes, otherwise raise 401
    Throttles based on failed attempts, Successful request do not count as attempts.
    """

    from config.auth import ForceCSRFAuthentication

    authentication_classes = [ForceCSRFAuthentication]
    permission_classes = [AllowAny]
    serializer_class = sc.LoginSerializer
    throttle_classes = [EmailScopedThrottle]
    throttle_scope = "failed_login_attempts"

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)
        user = user_authenticate(**incoming)
        # initialize the session
        login(request, user=user)

        # On login success, remove the attempt from history
        self.pop_latest_cache_entry(request)

        # Serialize data and respond
        outgoing = sc.UserDetailSerializer(instance=user)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)


class LogoutView(BaseAPIView):
    """
    Flush current user session and delete session_id cookie
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # First store the id to log later
        user_id = request.user.pk
        logout(request)
        logger.info(f"User [user_id: {user_id} logged out]")
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


class EmailUpdateView(BaseAPIView):
    """
    View allows users to change emails. Limited to once a weeka
    Moved throttling is based on the last_email_change field on the model.
    This centralizes the logic in one place
    """

    permission_classes = [IsAuthenticated]
    serializer_class = sc.UserEmailUpdateSerializer

    def post(self, request):
        incoming = self.validate_serializer(data=request.data, partial=False)
        user = user_email_update(user=request.user, **incoming)

        # In this case its better to respond with the email instead of the whole payload
        # Helps in front end rendering.
        return Response(data={"email": user.email}, status=status.HTTP_200_OK)


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
        user = user_change_password(user=request.user, **incoming)
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
        if not user.verified:
            send_token_email.delay(
                user_id=user.pk,
                url_path="email-verify",
                subject="Verify your email address.",
                action_cta="Verify Email",
            )
            logger.info(f"email verification request from [user_email: {user.email}]")
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
            user_email_verify(user)
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
            send_token_email.delay(
                user_id=user.pk,
                url_path="password-reset",
                subject="Reset your password",
                action_cta="Reset password",
            )
            logger.info(f"password reset request from [user_email: {user.email}]", user_id=user.pk)
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
        user_change_password(user=user, is_ressetting=True, **incoming)
        return Response(
            data={
                "message": "password has been reset successfully, other active sessions you had have now been logged out"
            },
            status=status.HTTP_200_OK,
        )


class UserUnsubscribeView(BaseAPIView):
    """
    Route to unregister users from mailing list and misc notifications
    """

    permission_classes = [AllowAny]

    def get(self, request, uidb64):
        user = get_user_from_uidb64(uidb64)
        if not user.account.can_receive_emails:
            account_unsubscribe(user.account)
        return Response(status=status.HTTP_200_OK)


class AdminUserRoleDetailView(BaseAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = sc.UserRoleCreateSerializer

    def get(self, request, user_id):
        user = user_get_for(user=request.user, user_id=user_id)
        serializer = sc.UserRoleDetailSerializer(instance=user)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def post(self, request, user_id):
        user = user_get_for(user=request.user, user_id=user_id)
        incoming = self.validate_serializer(data=request.data)
        user_add_role(user=user, role=incoming["role"])
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, user_id):
        user = user_get_for(user=request.user, user_id=user_id)
        user_remove_role(user=user)
        return Response(status=status.HTTP_200_OK)


class AdminUserRoleListView(BaseAPIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        groups = groups_list()
        serializer = sc.UserRoleListSerializer(many=True, instance=groups)
        return Response(status=status.HTTP_200_OK, data=serializer.data)
