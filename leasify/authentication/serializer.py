from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """Regular login requires email and password"""

    email = serializers.EmailField()
    password = serializers.CharField()


class RequestPasswordResetSerializer(serializers.Serializer):
    """Email required to send the reset link to"""

    email = serializers.EmailField()
    


class ConfirmPasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        data.pop("confirm_password")
        return data


class PasswordChangeSerializer(serializers.Serializer):
    """
    Inherits from BasePasswordSerializer
    Adds a current password field unlike password resets.
    """

    password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        data.pop("confirm_password")
        return data
