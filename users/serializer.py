from datetime import timedelta, timezone
from .models import User
from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework.validators import UniqueValidator


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Post request to create a user account. Requires 'email' and 'password' and
    optional 'first_name' and 'last_name'

    Uses aliases as the front end consumes camelcase.
    """

    firstName = serializers.CharField(
        source="first_name", required=False, allow_blank=True
    )
    lastName = serializers.CharField(
        source="last_name", required=False, allow_blank=True
    )

    class Meta:
        model = User
        fields = ["email", "password", "firstName", "lastName", "username"]

    def create(self, validated_data):
        user = User(
            email=validated_data["email"],
            first_name=validated_data.get("first_name"),
            last_name=validated_data.get("last_name"),
            username=validated_data.get("username"),
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class UserProfileEditSerializer(serializers.ModelSerializer):
    """
    Patch request to edit user's profile information:
    Optional "first_name", "last_name", "phoneNumber" "username" and "bio",
    """

    firstName = serializers.CharField(
        source="first_name", required=False, allow_blank=True
    )
    lastName = serializers.CharField(
        source="last_name", required=False, allow_blank=True
    )
    phoneNumber = PhoneNumberField(
        source="phone_number",
        region="KE",
        required=False,
        allow_blank=True,
        validators=[UniqueValidator(queryset=User.objects.all())],
    )

    class Meta:
        model = User
        fields = ["firstName", "lastName", "username", "bio", "phoneNumber"]
        extra_kwargs = {"username": {"required": False}}


class EmailChangeSerializer(serializers.ModelSerializer):
    """
    Patch request to change email. Requires 'newEmail' and 'currentPassword'
    """

    newEmail = serializers.EmailField(
        source="email",
        write_only=True,
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())],
    )
    currentPassword = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["newEmail", "currentPassword"]

    def validate_newEmail(self, value):
        if self.instance and self.instance.email == value:
            raise serializers.ValidationError(
                "New email and old email cannot be the same"
            )
        return value

    def validate_currentPassword(self, value):
        if self.instance is None or not self.instance.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def update(self, instance, validated_data):
        validated_data.pop("currentPassword")
        instance = super().update(instance, validated_data)
        instance.is_email_verified = False
        instance.save()
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    """
    Patch request to change password. Requires 'currentPassword' and 'newPassword'
    """

    currentPassword = serializers.CharField(write_only=True, required=True)
    newPassword = serializers.CharField(write_only=True, required=True)

    def validate_currentPassword(self, value):
        if self.instance is None or not self.instance.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def update(self, instance, validated_data):
        instance.set_password(validated_data["newPassword"])
        instance.save()
        return instance


class EmailForPasswordResetSerializer(serializers.Serializer):
    """
    Post request to check email validity. Requires 'email'

    Stashes a user in the instance created if email provided matches for user in the db
    """

    email = serializers.EmailField(write_only=True, required=True)

    def validate(self, attrs):
        try:
            user = User.objects.get(email=attrs["email"])
            attrs["user"] = user  # Stash the user to the validated_data
        except User.DoesNotExist:
            attrs["user"] = None

        return attrs


class PasswordResetSerializer(serializers.Serializer):
    """
    Patch request to reset password. Requires 'newPassword' and 'confirmPassword'
    """

    newPassword = serializers.CharField(write_only=True, required=True)
    confirmPassword = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        # Passwords already exist in attrs if attr upon field level validation
        # Now we check if they are the same
        if attrs.get("newPassword") == attrs.get("confirmPassword"):
            return attrs
        raise serializers.ValidationError({"confirmPassword": "Passwords do not match"})

    def update(self, instance, validated_data):
        instance.set_password(validated_data["newPassword"])
        instance.save()
        return instance


class UserRetrieveSerializer(serializers.ModelSerializer):
    """
    Get request to fetch required user information on load.
    email_change_cooldown and user_name_change_cooldown yet to be implemented.
    """

    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    isEmailVerified = serializers.BooleanField(source="is_email_verified")
    phoneNumber = PhoneNumberField(source="phone_number")
    nextUsernameChange = serializers.SerializerMethodField()
    nextEmailChange = serializers.SerializerMethodField()
    user_roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "username",
            "firstName",
            "lastName",
            "bio",
            "email",
            "phoneNumber",
            "roles",
            "nextUsernameChange",
            "isEmailVerified",
            "nextEmailChange",
        ]

    def get_nextUsernameChange(self, obj):
        return obj.get_next_available_username_change()

    def get_nextEmailChange(self, obj):
        return obj.get_next_available_email_change()
