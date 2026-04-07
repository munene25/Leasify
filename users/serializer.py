from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from django.contrib.auth.models import Group


class UserCreateSerializer(serializers.Serializer):
    """
    Need to set the boolean field's default value otherwise defaults to false
    """

    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField()
    phone_number = PhoneNumberField()
    notify = serializers.BooleanField(required=False, default=True)


class UserListSerializer(serializers.Serializer):
    """
    A List serializer indicating general user attributes.
    """

    user_id = serializers.IntegerField(source="pk")
    is_active = serializers.BooleanField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    verified = serializers.BooleanField()
    phone_number = PhoneNumberField(source="account.phone_number")


class UserUpdateSerializer(serializers.Serializer):
    """
    Detail serializer for users updating their own accounts.
    Instantiated with 'partial' flag.
    """

    first_name = serializers.CharField()
    last_name = serializers.CharField()
    # Account fields
    bio = serializers.CharField()
    backup_email = serializers.EmailField()
    phone_number = PhoneNumberField()


class UserDetailSerializer(serializers.Serializer):
    """
    Detail serializer for the requesting user.
    Adds a role(s) field inteded for frontend role based access
    """

    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    joined_at = serializers.DateTimeField(source="created_at")
    email_verified = serializers.BooleanField(source="verified")
    next_email_change = serializers.DateTimeField(allow_null=True)
    phone_number = PhoneNumberField(source="account.phone_number")
    backup_email = serializers.EmailField(source="account.backup_email", allow_null=True)
    bio = serializers.CharField(source="account.bio")
    role = serializers.CharField()


class AdminUserUpdateSerializer(serializers.Serializer):
    """
    Fields an admin can modify for other user.
    Allows only a subset of fields
    """

    first_name = serializers.CharField()
    last_name = serializers.CharField()
    # Account fields
    phone_number = PhoneNumberField()


class AdminUserDetailSerializer(UserDetailSerializer):
    """
    Extends the user detail serializer
    Intended for admins to have access to the user_id of the specified user.
    """

    user_id = serializers.IntegerField(source="pk")


class LoginSerializer(serializers.Serializer):
    """
    Email and password serializer.
    Password checking remains on the service.
    """

    email = serializers.EmailField()
    password = serializers.CharField()


class RequestPasswordResetSerializer(serializers.Serializer):
    """
    Email required to send the mail to
    """

    email = serializers.EmailField()


class BasePasswordSerializer(serializers.Serializer):
    """
    Base serializer
    Validates that the new_password and confirm password match
    """

    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        data.pop("confirm_password")
        return data


class ConfirmPasswordResetSerializer(BasePasswordSerializer):
    """
    Inherits from BasePasswordSerializer
    """

    pass


class PasswordChangeSerializer(BasePasswordSerializer):
    """
    Inherits from BasePasswordSerializer
    Adds a current password field unlike password resets.
    """

    password = serializers.CharField()


class UserEmailUpdateSerializer(serializers.Serializer):
    """
    Update serializer for users to update their own emails.
    Requires email to change to and current user password.
    """

    password = serializers.CharField()
    email = serializers.EmailField()


class UserRoleDetailSerializer(serializers.Serializer):
    """
    Requires the user object to passed as the instance to the serializer
    Roles is a lazy user attribute
    """

    user_id = serializers.IntegerField(source="pk")
    role = serializers.CharField()


class UserRoleCreateSerializer(serializers.Serializer):
    """
    A means to add roles to a user.
    User id is passed via the url.
    """

    role = serializers.SlugRelatedField(slug_field="name", queryset=Group.objects.all())


class UserRoleListSerializer(serializers.Serializer):
    """
    Instantiated with a groups qs.
    A list serializer for every name of group.
    """

    roles = serializers.CharField(source="name")
