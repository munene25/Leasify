from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.contrib.auth.models import Group
from rest_framework.status import HTTP_200_OK, HTTP_202_ACCEPTED, HTTP_204_NO_CONTENT
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from mixins import ValidateSerializerMixin, PermissionMixin
from .mixins import CookieMixin
from .tokens import token_validate, unsubscribe_token_validate
from .tasks import send_token_email
from .services import (
    user_create,
    user_login,
    profile_update,
    user_email_verify,
    user_change_password,
    user_delete_or_deactivate,
    account_unsubscribe,
)
from .selectors import (
    users_get_visible_for,
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
from .permissions import GuestsCanPostOnly
from domain.throttles import (
    AnonBurst,
    AnonSustained,
    UserBurst,
    UserSustained,
    ScopedRateThrottle,
    EmailBaseThrottle,
)


class UserListCreateView(APIView, ValidateSerializerMixin, PermissionMixin):
    serializer_class = UserCreateSerializer
    permission_classes = [GuestsCanPostOnly]
    throttle_classes = [AnonBurst, AnonSustained]

    def get(self, request):
        self.check_perms(request.user, "users.view_users")
        users = users_get_visible_for(request.user)
        serializer = UserListSerializer(instance=users, many=True)
        return Response(status=HTTP_200_OK, data=serializer.data)

    def post(self, request):
        data = self.validate_input(data=request.data)
        user_create(**data)
        return Response(status=HTTP_200_OK)


class UserDetailUpdateDestroyView(APIView, ValidateSerializerMixin, PermissionMixin):
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        self.check_perms(request.user, "user.view_user")
        user = user_get_by_id(user_id)
        serialzer_class = UserDetailSerializer(instance=user)
        return Response(status=HTTP_200_OK, data=serialzer_class.data)

    def put(self, request, user_id):
        self.check_perms(request.user, "user.edit_user")
        data = self.validate_input(data=request.data)
        user = user_get_by_id(user_id)
        profile_update(user=user, **data)
        return Response(status=HTTP_200_OK)

    def patch(self, request, user_id):
        self.check_perms(request.user, "user.edit_user")
        data = self.validate_input(data=request.data, partial=True)
        user = user_get_by_id(user_id)
        profile_update(user=user, **data)
        return Response(status=HTTP_200_OK)

    def delete(self, request, user_id):
        self.check_perms(request.user, "user.delete_user")
        user = user_get_by_id(user_id)
        res = user_delete_or_deactivate(user)
        if res is None:
            return Response(status=HTTP_204_NO_CONTENT)
        return Response(
            status=HTTP_200_OK,
            data={"message": "User deactivated, deletion not available"},
        )


class MeView(APIView, ValidateSerializerMixin, CookieMixin):
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = user_get_by_id(request.user.pk)
        serializer = UserDetailSerializer(instance=user)
        return Response(status=HTTP_200_OK, data=serializer.data)

    def put(self, request):
        data = self.validate_input(data=request.data)
        profile_update(user=request.user, **data)
        return Response(status=HTTP_200_OK)

    def patch(self, request):
        data = self.validate_input(data=request.data, partial=True)
        profile_update(user=request.user, **data)
        return Response(status=HTTP_200_OK)

    def delete(self, request):
        user_delete_or_deactivate(request.user)
        res = Response(status=HTTP_204_NO_CONTENT)
        response = self.del_cookies(cookies=["access", "refresh"], response=res)
        return response


class LoginView(APIView, ValidateSerializerMixin, CookieMixin):
    throttle_classes = [EmailBaseThrottle]
    throttle_scope = "login_limit"
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        data = self.validate_input(data=request.data)
        _, tokens = user_login(**data)
        res = Response(status=HTTP_200_OK)
        response = self.set_cookies(response=res, **tokens)
        return response


class LogoutView(APIView, CookieMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        res = Response(status=HTTP_200_OK)
        response = self.del_cookies(cookies=["access", "refresh"], response=res)
        return response


class RefreshTokenView(APIView, CookieMixin):
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


class PasswordChangeView(APIView, CookieMixin, ValidateSerializerMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer
    throttle_classes = [UserBurst, ScopedRateThrottle]
    throttle_scope = "password_changes"

    def post(self, request):
        data = self.validate_input(data=request.data)
        user_change_password(user=request.user, **data)
        return Response(status=HTTP_200_OK)


class RequestEmailVerificationView(APIView):
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
            )  # type: ignore
        return Response(status=HTTP_202_ACCEPTED)


class ConfirmEmailVerificationView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, uuid, token):
        user = token_validate(uuid=uuid, token=token)
        user_email_verify(user)
        return Response(status=HTTP_200_OK)


class RequestPasswordResetView(APIView, ValidateSerializerMixin):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = RequestPasswordResetSerializer
    throttle_classes = [AnonBurst, EmailBaseThrottle]
    throttle_scope = "email_verification"

    def post(self, request):
        data = self.validate_input(data=request.data)
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
            )  # type: ignore
        return Response(status=HTTP_202_ACCEPTED)


class ConfirmPasswordResetView(APIView, ValidateSerializerMixin):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = ConfirmPasswordResetSerializer

    def post(self, request, uuid, token):
        user = token_validate(uuid=uuid, token=token)
        data = self.validate_input(data=request.data)
        user_change_password(user=user, **data)
        return Response(status=HTTP_200_OK)


class UserUnsubscribeView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, uuid):
        user = unsubscribe_token_validate(uuid)
        account = getattr(user, "account")
        account_unsubscribe(account)
        return Response(status=HTTP_200_OK)


class UserRoleDetailView(APIView, ValidateSerializerMixin):
    permission_classes = [IsAdminUser]
    serializer_class = UserRoleCreateSerializer

    def get(self, request, user_id):
        user = user_get_by_id(user_id)
        serializer = UserRoleDetailSerializer(instance=user)
        return Response(status=HTTP_200_OK, data=serializer.data)

    def post(self, request, user_id):
        user = user_get_by_id(user_id)
        data = self.validate_input(data=request.data)
        user.groups.add(*data["roles"])
        return Response(status=HTTP_200_OK)

    def delete(self, request, user_id):
        user = user_get_by_id(user_id)
        data = self.validate_input(data=request.data)
        user.groups.remove(*data["roles"])
        return Response(status=HTTP_200_OK)


class UserRoleListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        groups = Group.objects.all()
        serializer = UserRoleListSerializer(many=True, instance=groups)
        return Response(status=HTTP_200_OK, data=serializer.data)
