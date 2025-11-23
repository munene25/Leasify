# utils.py
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.conf import settings
from .models import User


def generate_token(user: AbstractUser) -> tuple:
    """
    This  is responsible for encoding the user id and generating a token based on the user.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


def build_verification_url(user: AbstractUser, path: str) -> str:
    """
    Responsible for creating a clickable front end url based on the user and path
    """
    uid, token = generate_token(user)
    # build absolute URL e.g., https://yourdomain.com/api/verify-email/<uid>/<token>/
    url = f"{settings.FRONTEND_URL}/{path}/{uid}/{token}/"
    return url


def validate_token(uidb64: str, token: str) -> AbstractUser | None:
    """
    Responsible for validating the token by checking the uidb64 to map to a user and token to check validity. Returns either a valid User Object or None
    """
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None

    if default_token_generator.check_token(user, token):
        return user
    return None


def send_verification_email(user):
    verification_url = build_verification_url(user, "verify-email")
    subject = "Verify your email"
    message = (
        f"Greetings {user.username},\n\n"
        "Thank you for signing up.\n"
        "Please verify your email by clicking the link below:\n\n"
        f"{verification_url}\n\n"
        "If you did not create this account, you can ignore this email.\n\n"
        "Best regards,\n"
        "YourAppName Team\n"
        "@no-reply"
    )

    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)


def send_password_reset_email(user):
    reset_url = build_verification_url(user, "confirm/password-reset")
    subject = "Password Reset link"
    message = (
        f"Greetings {user.username},\n\n"
        "We received a request to reset your password.\n"
        "You can reset it by clicking the link below:\n\n"
        f"{reset_url}\n\n"
        "If you did not request a password reset, please ignore this email.\n\n"
        "Best regards,\n"
        "YourAppName Team\n"
        "@no-reply"
    )
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
