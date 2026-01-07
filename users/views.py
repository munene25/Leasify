from rest_framework.request import Request
from rest_framework.response import Response
from . import serializer as app_serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.generics import CreateAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from .utils import validate_token, send_verification_email, send_password_reset_email


def _set_cookies(response: Response, key: str, value: str) -> None:
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=False,
        samesite="Lax",
    )


def _clear_cookies(response: Response, *args) -> None:
    for arg in args:
        response.delete_cookie(arg)


class SignUpView(CreateAPIView):
    """
    Handles user creation and sending verification email.
    """

    permission_classes = [AllowAny]
    serializer_class = app_serializers.UserCreateSerializer

    # Send the email after the user is created not in post
    def perform_create(self, serializer):
        user = serializer.save()
        send_verification_email(user)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]

    def post(self, request: Request, *args, **kwargs) -> Response:
        # Call the parent class's post method to handle token generation.
        # This will return a Response with tokens in the data or an error.
        response = super().post(request, *args, **kwargs)

        # Check if the token generation was successful (status code 200).
        if response.status_code == 200 and response.data is not None:
            tokens = response.data
            access_token = tokens.get("access")
            refresh_token = tokens.get("refresh")
            response.data = {
                "message": "Successfully Logged in"
            }  # overwrite the data attribute

            # Set the cookies on the response
            _set_cookies(response, "access", access_token)
            _set_cookies(response, "refresh", refresh_token)

        # Return the original response, whether it's a success or an error.
        return response


class RefreshTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        refresh_token = request.COOKIES.get("refresh")

        # If no refresh token is in the cookies, return an error.
        if not refresh_token:
            return Response(
                {"message": "Refresh token not found in cookies"},
                status.HTTP_401_UNAUTHORIZED,
            )
        try:
            serializer_data = TokenRefreshSerializer(data={"refresh": refresh_token})
            serializer_data.is_valid(raise_exception=True)
            access_token = serializer_data.validated_data["access"]  # type: ignore
            response = Response(
                {"message": "Refreshed token successfully"}, status=status.HTTP_200_OK
            )
            _set_cookies(response, "access", access_token)
            return response
        except TokenError as e:
            return Response(
                {"message": f"Token Error: {e}"},
                status.HTTP_401_UNAUTHORIZED,
            )
        except InvalidToken as e:
            return Response(
                {"message": f"Invalid Token: {e}"},
                status.HTTP_401_UNAUTHORIZED,
            )



class UpdateUserProfile(UpdateAPIView):
    serializer_class = app_serializers.UserProfileEditSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self): # type: ignore
        return self.request.user
    
class PasswordChangeView(UpdateAPIView):
    serializer_class = app_serializers.PasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):  # type: ignore
        return self.request.user


class EmailChangeView(UpdateAPIView):
    serializer_class = app_serializers.EmailChangeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):  # type: ignore
        return self.request.user


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = Response({"message": "Successfully signed out"})
        _clear_cookies(response, "access", "refresh")
        return response


class SendEmailVerificationLinkView(APIView):
    """
    This view is responsible for generating an email verification link that directs the user to the front end.

    Accepts a post request with the email to send the link to.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        user = request.user
        if not user.is_email_verified:
            send_verification_email(user)
            return Response(
                {"message": "A verification link has been sent to your email."},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"email": "Email is already verified"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class VerifyEmailTokenView(APIView):
    """
    This view is repsonsible for accepting a token and uuid in the url and set email as verified.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, uidb64, token):
        user = validate_token(uidb64, token)
        if user:
            user.is_email_verified = True  # type: ignore
            user.save()
            return Response(
                {"message": "Email verified successfully"}, status.HTTP_200_OK
            )
        else:
            return Response(
                {"message": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SendPasswordResetLinkView(APIView):
    """
    This view is responsible for generating a password reset link that directs the user to the front end.

    Accepts a post request with an email to send the link to.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = app_serializers.EmailForPasswordResetSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data.get("user")  # type: ignore
            if user:
                send_password_reset_email(user)
            return Response(
                {
                    "message": "An email with a password reset link has been sent to the email provided."
                },
                status=status.HTTP_200_OK,
            )
        # Only return a 'provide email response' for missing or malformed emails.
        return Response(
            {"email": "Please provide an email address"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class VerifyPasswordTokenView(APIView):
    """
    This view is repsonsible for accepting a token and uuid in the url and perform password update action.
    """

    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        user = validate_token(uidb64, token)

        if not user:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = app_serializers.PasswordResetSerializer(data=request.data)

        if serializer.is_valid():
            validated_data = serializer.validated_data
            serializer.update(user, validated_data)

            return Response(
                {"message": "Password update successful"},
                status=status.HTTP_200_OK,
            )

        # Return the actual serializer errors for more accurate feedback
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class GetUserData(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = app_serializers.UserRetrieveSerializer
    
    def get_object(self): # type: ignore
        return self.request.user
    