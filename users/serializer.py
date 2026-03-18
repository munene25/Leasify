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
    user_id = serializers.IntegerField(source="pk")
    is_active = serializers.BooleanField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    verified = serializers.BooleanField()
    phone_number = PhoneNumberField(source="account.phone_number")


class UserUpdateSerializer(serializers.Serializer):
    """ This serializer is instantiated with 'partial' flag"""
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    # Account fields
    bio = serializers.CharField()
    backup_email = serializers.EmailField()
    phone_number = PhoneNumberField()


class UserDetailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    joined_at = serializers.DateTimeField(source="created_at")
    email_verified = serializers.BooleanField(source="verified")
    next_email_change = serializers.DateTimeField(allow_null=True)
    phone_number = PhoneNumberField(source="account.phone_number")
    backup_email = serializers.EmailField(source="account.backup_email", allow_null=True)
    bio = serializers.CharField(source="account.bio")
    roles = serializers.ListField()

class AdminUserUpdateSerializer(serializers.Serializer):
    """Fields an admin can modify for the user"""
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    # Account fields
    phone_number = PhoneNumberField()

class AdminUserDetailSerializer(UserDetailSerializer):
    """Admin serializer for user details. Includes a crucial user_id"""
    user_id = serializers.IntegerField(source="pk")


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class BasePasswordSerializer(serializers.Serializer):
    """
    Base password serializer with confirm password validation
    """
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        data.pop("confirm_password")
        return data


class ConfirmPasswordResetSerializer(BasePasswordSerializer):
    pass


class PasswordChangeSerializer(BasePasswordSerializer):
    password = serializers.CharField()


class UserEmailUpdateSerializer(serializers.Serializer):
    password = serializers.CharField()
    email = serializers.EmailField()


class UserRoleDetailSerializer(serializers.Serializer):
    """
    Instantiated with a user object
    Roles is a user attribute
    """
    roles = serializers.ListField()


class UserRoleCreateSerializer(serializers.Serializer):
    roles = serializers.SlugRelatedField(slug_field="name", many=True, queryset=Group.objects.all())


class UserRoleListSerializer(serializers.Serializer):
    name = serializers.CharField()
