from structlog import getLogger
from django.contrib.auth.models import Group
from common.views import BaseAPIView
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.status import HTTP_200_OK, HTTP_202_ACCEPTED, HTTP_204_NO_CONTENT
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from common.validators import validate_serializer, validate_filter
from common.permissions import check_perms
from common.pagination import get_paginated_response
from common.throttling import (
    AnonBurst,
    AnonSustained,
    UserBurst,
    ScopedRateThrottle,
    EmailBaseThrottle,
)
from .mixins import CookieMixin
from .tokens import token_validate, unsubscribe_token_validate
from .tasks import send_token_email
from .services import (
    user_account_create,
    user_login,
    user_account_update,
    user_email_verify,
    user_change_password,
    user_delete_or_deactivate,
    account_unsubscribe,
)
from .selectors import (
    user_list,
    user_get_by_id,
    user_get_by_email,
)
from .serializer import (
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
)

logger = getLogger("users.views")


class UserListCreateView(BaseAPIView):
    serializer_class = UserCreateSerializer
    throttle_classes = [AnonBurst, AnonSustained]

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        email = serializers.CharField()
        first_name = serializers.CharField()
        last_name = serializers.CharField()
        phone_number = serializers.CharField()

    def get(self, request):

        check_perms(request.user, "users.view_users")
        filters = validate_filter(
            s_cls=self.FilterSerializer, data=request.query_params, partial=True
        )
        qs = user_list(filters)

        return get_paginated_response(
            serializer_class=UserListSerializer, queryset=qs, request=request, view=self
        )

    def post(self, request):
        data = validate_serializer(s_cls=self.serializer_class, data=request.data)
        user_account_create(**data)
        return Response(status=HTTP_200_OK)


class UserDetailUpdateDestroyView(BaseAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        check_perms(request.user, "user.view_user")
        user = user_get_by_id(user_id)
        serialzer_class = UserDetailSerializer(instance=user)

        return Response(status=HTTP_200_OK, data=serialzer_class.data)

    def put(self, request, user_id):
        check_perms(request.user, "user.edit_user")
        data = validate_serializer(s_cls=self.serializer_class, data=request.data)
        user = user_get_by_id(user_id)

        if user.is_superuser or user.is_staff:
            logger.warning(
                f"modifying staff user data data not allowed. Target[user_id: {user_id}]"
            )
            raise PermissionDenied()

        user_account_update(user=user, **data)
        logger.info(f"admin modified user data. [user_id: {user_id}]")
        return Response(status=HTTP_200_OK)

    def patch(self, request, user_id):
        check_perms(request.user, "user.edit_user")
        data = validate_serializer(
            s_cls=self.serializer_class, data=request.data, partial=True
        )
        user = user_get_by_id(user_id)
        if user.is_superuser or user.is_staff:
            logger.warning(
                f"modifying staff user data data not allowed. Target[user_id: {user_id}]"
            )
            raise PermissionDenied()

        user_account_update(user=user, **data)
        logger.info(f"Admin modified user data. [user_id: {user_id}] data")
        return Response(status=HTTP_200_OK)

    def delete(self, request, user_id):
        check_perms(request.user, "user.delete_user")
        user = user_get_by_id(user_id)
        if user.is_superuser or user.is_staff:
            logger.warning(
                f"modifying staff user data data not allowed. Target[user_id: {user_id}]"
            )
            raise PermissionDenied()

        res = user_delete_or_deactivate(user=user)
        if res is None:
            logger.info(f"Admin deleted user. [user_id: {user_id}]")
            return Response(status=HTTP_204_NO_CONTENT)
        logger.info(f"Admin deactivated user. [user_id: {user_id}]")
        return Response(
            status=HTTP_200_OK,
            data={"message": "User deactivated, deletion not available"},
        )


class MeView(BaseAPIView, CookieMixin):
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = user_get_by_id(request.user.pk)
        serializer = UserDetailSerializer(instance=user)
        return Response(status=HTTP_200_OK, data=serializer.data)

    def put(self, request):
        data = validate_serializer(s_cls=self.serializer_class, data=request.data)
        user_account_update(user=request.user, **data)
        return Response(status=HTTP_200_OK)

    def patch(self, request):
        data = validate_serializer(
            s_cls=self.serializer_class, data=request.data, partial=True
        )
        user_account_update(user=request.user, **data)
        return Response(status=HTTP_200_OK)

    def delete(self, request):
        user_delete_or_deactivate(user=request.user)
        res = Response(status=HTTP_204_NO_CONTENT)
        logger.info(f"User deleted self.")
        response = self.del_cookies(cookies=["access", "refresh"], response=res)
        return response


class LoginView(BaseAPIView, CookieMixin):
    throttle_classes = [EmailBaseThrottle]
    throttle_scope = "login_limit"
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        data = validate_serializer(s_cls=self.serializer_class, data=request.data)
        user, tokens = user_login(**data)
        res = Response(status=HTTP_200_OK)
        response = self.set_cookies(response=res, **tokens)
        return response


class LogoutView(BaseAPIView, CookieMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        res = Response(status=HTTP_200_OK)
        response = self.del_cookies(cookies=["access", "refresh"], response=res)
        logger.info(f"Logout successful")
        return response


class RefreshTokenView(BaseAPIView, CookieMixin):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonBurst, AnonSustained]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh")
        if not refresh_token:
            raise InvalidToken()
        try:
            refresh = RefreshToken(refresh_token)
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            tokens = {"refresh": refresh, "access": refresh.access_token}
            res = Response(status=HTTP_200_OK)
            response = self.set_cookies(response=res, **tokens)
            return response
        except TokenError:
            raise InvalidToken()


class PasswordChangeView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer
    throttle_classes = [UserBurst, ScopedRateThrottle]
    throttle_scope = "password_changes"

    def post(self, request):
        data = validate_serializer(s_cls=self.serializer_class, data=request.data)
        user_change_password(user=request.user, **data)
        return Response(status=HTTP_200_OK)


class RequestEmailVerificationView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserBurst, ScopedRateThrottle]
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
        return Response(status=HTTP_202_ACCEPTED)


class ConfirmEmailVerificationView(BaseAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, uuid, token):
        user = token_validate(uuid=uuid, token=token)
        user_email_verify(user)
        return Response(status=HTTP_200_OK)


class RequestPasswordResetView(BaseAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = RequestPasswordResetSerializer
    throttle_classes = [AnonBurst, EmailBaseThrottle]
    throttle_scope = "email_verification"

    def post(self, request):
        data = validate_serializer(s_cls=self.serializer_class, data=request.data)
        try:
            user = user_get_by_email(data["email"])
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
        return Response(status=HTTP_202_ACCEPTED)


class ConfirmPasswordResetView(BaseAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = ConfirmPasswordResetSerializer

    def post(self, request, uuid, token):
        user = token_validate(uuid=uuid, token=token)
        data = validate_serializer(s_cls=self.serializer_class, data=request.data)
        user_change_password(user=user, **data)
        return Response(status=HTTP_200_OK)


class UserUnsubscribeView(BaseAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, uuid):
        user = unsubscribe_token_validate(uuid)
        account = getattr(user, "account")
        account_unsubscribe(account)
        return Response(status=HTTP_200_OK)


class UserRoleDetailView(BaseAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = UserRoleCreateSerializer

    def get(self, request, user_id):
        user = user_get_by_id(user_id)
        serializer = UserRoleDetailSerializer(instance=user)
        return Response(status=HTTP_200_OK, data=serializer.data)

    def post(self, request, user_id):
        user = user_get_by_id(user_id)
        data = validate_serializer(s_cls=self.serializer_class, data=request.data)
        user.groups.add(*data["roles"])
        logger.info(
            f"Admin added [roles {data["roles"]}] for [user_id: {user_id}]"
        )

        return Response(status=HTTP_200_OK)

    def delete(self, request, user_id):
        user = user_get_by_id(user_id)
        data = validate_serializer(s_cls=self.serializer_class, data=request.data)
        user.groups.remove(*data["roles"])
        logger.info(
            f"Admin removed [roles: {data["roles"]}] from [user_id: {user.pk}]",
        )

        return Response(status=HTTP_200_OK)


class UserRoleListView(BaseAPIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        groups = Group.objects.all()
        serializer = UserRoleListSerializer(many=True, instance=groups)
        return Response(status=HTTP_200_OK, data=serializer.data)
