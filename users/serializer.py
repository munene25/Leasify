from .models import User
from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework.validators import UniqueValidator


class UserCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = PhoneNumberField()
    notify = serializers.BooleanField(required=False)


class UserListSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(source="pk")
    full_name = serializers.SerializerMethodField(method_name="get_full_name")
    email = serializers.EmailField()
    verified = serializers.BooleanField()
    phone_number = PhoneNumberField(
        source="account.phone_number",
        allow_null=True,
        required=False,
    )

class UserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    current_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    # Account fields
    phone_number = PhoneNumberField()
    bio = serializers.CharField()
    backup_email = serializers.EmailField()

class UserDetailSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    backup_email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email_verified = serializers.BooleanField(source="verified")
    joined_at = serializers.DateTimeField(source="created_at")
    phone_number = PhoneNumberField(
        source="account.phone_number",
        allow_null=True,
    )
    bio = serializers.CharField(allow_null=True)
    next_email_change = serializers.DateTimeField(allow_null=True)
    roles = serializers.ListSerializer(child=serializers.CharField())


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()
    
    def validate_confirm_password(self, value):
        if self.new_password != value:
            raise serializers.ValidationError("Passwords do not match")

class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ConfirmPasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()
    
    def validate_confirm_password(self, value):
        if self.new_password != value:
            raise serializers.ValidationError("Passwords do not match")
