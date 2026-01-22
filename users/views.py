from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.status import HTTP_200_OK, HTTP_202_ACCEPTED, HTTP_204_NO_CONTENT
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken
from .mixins import CookieMixin
from mixins import ValidateSerializerMixin
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
)
from .permissions import GuestCanCreateOnly, ManagersAllCaretakerViewOnly, IsPrivilegedAll


class UserListCreateView(APIView, ValidateSerializerMixin):
    serializer_class = UserCreateSerializer
    permission_classes = [GuestCanCreateOnly]

    def get(self, request):
        users = users_get_visible_for(request.user)
        serializer = UserListSerializer(instance=users, many=True)
        return Response(status=HTTP_200_OK, data=serializer.data)

    def post(self, request):
        data = self.validate_input(data=request.data)
        user_create(**data)
        return Response(status=HTTP_200_OK)


class UserDetailUpdateDestroyView(APIView, ValidateSerializerMixin):
    serializer_class = UserUpdateSerializer
    permission_classes = [ManagersAllCaretakerViewOnly]

    def get(self, request, user_id):
        user = user_get_by_id(user_id)
        serialzer_class = UserDetailSerializer(instance=user)
        return Response(status=HTTP_200_OK, data=serialzer_class.data)

    def put(self, request, user_id):
        data = self.validate_input(data=request.data)
        user = user_get_by_id(user_id)
        profile_update(user=user, **data)
        return Response(status=HTTP_200_OK)

    def patch(self, request, user_id):
        data = self.validate_input(data=request.data, partial=True)
        user = user_get_by_id(user_id)
        profile_update(user=user, **data)
        return Response(status=HTTP_200_OK)

    def delete(self, request, user_id):
        user = user_get_by_id(user_id)
        res = user_delete_or_deactivate(user)
        if res is None:
            return Response(status=HTTP_204_NO_CONTENT)
        return Response(status=HTTP_200_OK, data={"message": "User deactivated, deletion not available"})

class MeView(APIView, ValidateSerializerMixin, CookieMixin):
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = user_get_by_id(request.user.pk)
        serialzer_class = UserDetailSerializer(instance=user)
        return Response(status=HTTP_200_OK, data=serialzer_class.data)

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
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        data = self.validate_input(data=request.data)
        _ , tokens = user_login(**data)
        response = Response(status=HTTP_200_OK)
        self.set_cookies(response=response, **tokens)
        return response


class LogoutView(APIView, CookieMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        res = Response(status=HTTP_200_OK)
        response = self.del_cookies(cookies=["access", "refresh"], response=res)
        return response


class RefreshTokenView(APIView, CookieMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh")
        if not refresh_token:
            raise InvalidToken()
        tokens = {}
        tokens["refresh"] = RefreshToken(refresh_token)
        tokens["access"] = tokens["refresh"].access_token
        res = Response(status=HTTP_200_OK)
        response = self.set_cookies(response=res, **tokens)
        return response


class PasswordChangeView(APIView, CookieMixin, ValidateSerializerMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    def post(self, request):
        data = self.validate_input(data=request.data)
        user_change_password(user=request.user, **data)
        return Response(status=HTTP_200_OK)


class RequestEmailVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.verified:
            send_token_email.delay(
                user_id=user.pk,
                url_path="email-verify",
                subject="Verify your email address.",
                action_cta="Verify Email",
            )
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
            )
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