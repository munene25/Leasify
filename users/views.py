from structlog import getLogger
from common.views import BaseAPIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework import status
from common.permissions import check_perms
from django.contrib.auth import login, logout, update_session_auth_hash
from common.pagination import get_paginated_response
from common.throttling import (
    AnonSustained,
    EmailScopedThrottle,
)
from users.tokens import token_validate, unsubscribe_token_validate
from users.tasks import send_token_email
from users.services import (
    user_account_create,
    user_add_roles,
    user_authenticate,
    user_update,
    user_email_update,
    user_email_verify,
    user_change_password,
    user_deactivate,
    user_remove_roles,
    account_unsubscribe,
)
from users.selectors import (
    user_list_for,
    user_get_for,
    user_get,
    user_get_by_email,
    groups_list,
)
from users.serializer import (
    UserCreateSerializer,
    UserListSerializer,
    UserUpdateSerializer,
    UserDetailSerializer,
    PasswordChangeSerializer,
    RequestPasswordResetSerializer,
    ConfirmPasswordResetSerializer,
    LoginSerializer,
    UserRoleCreateSerializer,
    UserRoleDetailSerializer,
    UserRoleListSerializer,
    UserEmailUpdateSerializer,
)

logger = getLogger("users.views")


class UserListCreateView(BaseAPIView):
    """
    Provides a way to view the list (depending on the level of access) of registered users
    Also a create user via post

    The get method is a priviledged route hence permissions are checked and _for selectors are used 
    """
    class FilterSerializer(serializers.Serializer):
        search = serializers.CharField()
        is_active = serializers.BooleanField(allow_null=True)

    serializer_class = UserCreateSerializer
    throttle_classes = [AnonSustained]
    filter_class = FilterSerializer
    
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        else: return []
        
    def get(self, request: Request):
        check_perms(request.user, "users.view_user")
        filters = self.validate_filter(data=request.query_params)
        qs = user_list_for(user=request.user, filters=filters)
        return get_paginated_response(s_cls=UserListSerializer, qs=qs, req=request, view=self)

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)
        user_account_create(**incoming)
        return Response(status=status.HTTP_201_CREATED)


class UserDetailUpdateDestroyView(BaseAPIView):
    """
    Allows Admins or Authroized groups to modify users details
    All methods require priviledged access
    Selectors with _for should be used
    """
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        check_perms(request.user, "users.view_user")
        user = user_get_for(user= request.user ,user_id=user_id)
        serialzer_class = UserDetailSerializer(instance=user)
        return Response(status=status.HTTP_200_OK, data=serialzer_class.data)

    def patch(self, request, user_id):
        check_perms(request.user, "users.change_user")
        incoming = self.validate_serializer(data=request.data, partial=True)
        user = user_get_for(user= request.user ,user_id=user_id)
        mod = user_update(user, **incoming)
        outgoing = UserDetailSerializer(instance=mod)
        logger.info(f"Admin modified user data. [user_id: {user_id}] data")

        return Response(data=outgoing.data, status=status.HTTP_200_OK)

    def delete(self, request, user_id):
        check_perms(request.user, "users.delete_user")
        user = user_get_for(user=request.user, user_id=user_id)
        user_deactivate(user=user)
        logger.info(f"Admin deactivated user.", target_id=user_id)
        return Response(
            status=status.HTTP_200_OK,
            data={"message": "User deactivated"},
        )


class MeView(BaseAPIView):
    """
    This is the self management view for users to modify their own data
    """
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = user_get(request.user.pk)
        serializer = UserDetailSerializer(instance=user)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def patch(self, request):
        incoming = self.validate_serializer(data=request.data, partial=True)
        user_update(user=request.user, **incoming)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request):
        user_deactivate(user=request.user)
        
        logger.info(f"User deactivated self.")
        # Remove and flush the session
        logout(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginView(BaseAPIView):
    """Initializes the session on user authentication"""

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    throttle_classes = [EmailScopedThrottle]
    throttle_scope = "login_limit"

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)
        user = user_authenticate(**incoming)
        # initialize the session
        login(request, user=user)
        # ? Could add the session_key on the session itself for easy management
        outgoing = UserDetailSerializer(instance=user)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)

class LogoutView(BaseAPIView):
    """Delete current user session from the cache"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # First store the id to log later
        user_id = request.user.pk
        logout(request)
        logger.info(f"User [user_id: {user_id} logged out]")
        return Response(data={"message": "You have been logged out"}, status=status.HTTP_200_OK)

class RefreshSession(BaseAPIView):
    """frontend should on page mount or on interval hit 'refresh' to extend the session lifespan currently set to 2 weeks"""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
       request.session.set_expiry(None)
       return Response({"message": "Session refreshed"})


class EmailUpdateView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserEmailUpdateSerializer
    throttle_classes = [EmailScopedThrottle]
    throttle_scope = "email_change"

    def post(self, request, view):
        incoming = self.validate_serializer(data=request.data, partial=False)
        user_email_update(user=request.user, **incoming)
        return Response(status=status.HTTP_200_OK)


class PasswordChangeView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer
    throttle_classes = [EmailScopedThrottle]
    throttle_scope = "password_changes"

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)
        user_change_password(user=request.user, **incoming)
        update_session_auth_hash(request, request.user)
        return Response(status=status.HTTP_200_OK)


class RequestEmailVerificationView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [EmailScopedThrottle]
    throttle_scope = "email_verification"

    def post(self, request):
        user = request.user
        if not user.verified:
            send_token_email.delay(
                user_id=user.pk,
                url_path="email-verify",
                subject="Verify your email address.",
                action_cta="Verify Email",
            )
            logger.info(
                "User email verification request",
                extra={"actor": f"user: {request.user}"},
            )
        return Response(status=status.HTTP_202_ACCEPTED)


class ConfirmEmailVerificationView(BaseAPIView):

    permission_classes = [AllowAny]

    def post(self, request, uuid, token):
        user = token_validate(uuid=uuid, token=token)
        if not user.verified:
            user_email_verify(user)
        return Response(status=status.HTTP_200_OK)


class RequestPasswordResetView(BaseAPIView):

    permission_classes = [AllowAny]
    serializer_class = RequestPasswordResetSerializer
    throttle_classes = [EmailScopedThrottle]
    throttle_scope = "email_verification"

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
            logger.info("User request password reset")
        return Response(status=status.HTTP_202_ACCEPTED)


class ConfirmPasswordResetView(BaseAPIView):

    permission_classes = [AllowAny]
    serializer_class = ConfirmPasswordResetSerializer

    def post(self, request, uuid, token):
        user = token_validate(uuid=uuid, token=token)
        incoming = self.validate_serializer(data=request.data)
        user_change_password(user=user, **incoming)
        return Response(status=status.HTTP_200_OK)


class UserUnsubscribeView(BaseAPIView):
    permission_classes = [AllowAny]

    def get(self, request, uuid):
        user = unsubscribe_token_validate(uuid)
        if not user.account.can_receive_emails:
            account_unsubscribe(user.account)
        return Response(status=status.HTTP_200_OK)


class UserRoleDetailView(BaseAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = UserRoleCreateSerializer

    def get(self, request, user_id):
        user = user_get_for(user=request.user, user_id=user_id)
        serializer = UserRoleDetailSerializer(instance=user)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def post(self, request, user_id):
        user = user_get_for(user=request.user, user_id=user_id)
        incoming = self.validate_serializer(data=request.data)
        user_add_roles(user=user, roles=incoming["roles"])
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, user_id):
        user = user_get_for(user=request.user, user_id=user_id)
        incoming = self.validate_serializer(data=request.data)
        user_remove_roles(user=user, roles=incoming["roles"])
        return Response(status=status.HTTP_200_OK)


class UserRoleListView(BaseAPIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        groups = groups_list()
        serializer = UserRoleListSerializer(many=True, instance=groups)
        return Response(status=status.HTTP_200_OK, data=serializer.data)
