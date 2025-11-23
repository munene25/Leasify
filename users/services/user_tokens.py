from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from rest_framework.exceptions import ValidationError, NotFound
from ..selectors import user_get_by_email, user_get_by_id
from ..mixins import EmailSenderMixin

class UserTokenService(EmailSenderMixin):
    def __init__(self):
        pass
    def _get_user(self, *, user_email=None, user_id=None):
        if user_email:
            return user_get_by_email(user_email=user_email)
        if user_id:
            return user_get_by_id(user_id=user_id)
        raise ValueError("Provide either user_email or user_id")

    def _make_uuid_and_token(self, user):
        uuid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return uuid, token

    def _build_url(self, *, path, uuid, token):
        if not path:
            raise ValueError("Path not provided")
        return f"{self.frontend_url}/{path}/{uuid}/{token}"

    def validate_token(self, *, uuid, token):
        try:
            user_id = force_str(urlsafe_base64_decode(uuid))
            user = self._get_user(user_id=user_id)
        except NotFound:
            raise ValidationError("Invalid user token")

        if not default_token_generator.check_token(user, token):
            raise ValidationError("Invalid or expired token")
        return user

    def send_verification_email(self, *, user_email):
        path = "verify-email"
        user = self._get_user(user_email=user_email)
        uuid, token = self._make_uuid_and_token(user)
        url = self._build_url(path=path, uuid=uuid, token=token)
        subject = "Verify your email"
        context = {
            "user": user,
            "url": url,
            "subject": subject,
            "expiry_hours": 72,
            "preheader": "Confirm your email to get started",
            "unsubscribe_url": f"{self.frontend_url}/unsubscribe/{uuid}",
        }
        self._send_template_email(
            subject,
            "emails/verify.html",
            "emails/verify.txt",
            context,
            user.email,
        )

    def send_password_reset_email(self, *, user_email, path):
        user = self._get_user(user_email=user_email)
        uuid, token = self._make_uuid_and_token(user)
        url = self._build_url(path=path, uuid=uuid, token=token)

        subject = "Password Reset Link"
        context = {
            "user": user,
            "url": url,
            "subject": subject,
            "expiry_hours": 72,
            "preheader": "Confirm your email to get started",
            "unsubscribe_url": f"{settings.FRONTEND_URL}/unsubscribe/{uuid}",
        }
        self._send_template_email(
            subject,
            "emails/reset.html",
            "emails/reset.txt",
            context,
            user.email,
        )
