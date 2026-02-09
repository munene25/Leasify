from .models import User
from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework.validators import UniqueValidator
from django.contrib.auth.models import Group

class UserCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField()
    phone_number = PhoneNumberField()
    notify = serializers.BooleanField(required=False)


class UserListSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(source="pk")
    full_name = serializers.CharField()
    email = serializers.EmailField()
    verified = serializers.BooleanField()
    phone_number = PhoneNumberField(
        source="account.phone_number",
        allow_null=True,
        required=False,
    )

class UserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    # Account fields
    phone_number = PhoneNumberField(write_only=True)
    bio = serializers.CharField(write_only=True)
    backup_email = serializers.EmailField(write_only=True)

class UserDetailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    backup_email = serializers.EmailField(source="account.backup_email", allow_null=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email_verified = serializers.BooleanField(source="verified")
    joined_at = serializers.DateTimeField(source="created_at")
    phone_number = PhoneNumberField(
        source="account.phone_number",
        allow_null=True,
    )
    bio = serializers.CharField(source="account.bio", allow_null=True)
    next_email_change = serializers.DateTimeField(allow_null=True)
    roles = serializers.ListField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()
    
    def validate(self, data):
        if data.get('new_password') != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data

class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ConfirmPasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()
    
    def validate_confirm_password(self, value):
        if self.new_password != value:
            raise serializers.ValidationError("Passwords do not match")
        
class UserRoleDetailSerializer(serializers.Serializer):
    roles = serializers.ListField()

class UserRoleCreateSerializer(serializers.Serializer):
    roles = serializers.SlugRelatedField(slug_field="name", many=True, queryset=Group.objects.all())

class UserRoleListSerializer(serializers.Serializer):
    name = serializers.CharField()
    permissions = serializers.StringRelatedField(many=True)