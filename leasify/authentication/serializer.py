from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """Regular login requires email and password"""

    email = serializers.EmailField()
    password = serializers.CharField()


class RequestPasswordResetSerializer(serializers.Serializer):
    """Email required to send the reset link to"""

    email = serializers.EmailField()
    url_path = serializers.CharField()


class ConfirmPasswordResetSerializer(serializers.Serializer):
    """Does not require current password"""

    new_password = serializers.CharField()

class RequestEmailVerificationSerializer(serializers.Serializer):
    """Provide url path for the frontend path"""

    url_path = serializers.CharField()

class PasswordChangeSerializer(serializers.Serializer):
    """Requires current password as well as new password"""

    password = serializers.CharField()
    new_password = serializers.CharField()
