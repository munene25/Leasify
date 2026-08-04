from rest_framework import serializers
from leasify.common.fields import NameSerializerField, PhoneNumberSerializerField
from django.contrib.auth.models import Group


class UserCreateSerializer(serializers.Serializer):
    """
    Need to set the boolean field's default value otherwise defaults to false
    """

    first_name = NameSerializerField()
    last_name = NameSerializerField()
    email = serializers.EmailField()
    password = serializers.CharField()
    phone_number = PhoneNumberSerializerField()
    notify = serializers.BooleanField(required=False, default=True)
    unsubscribe_url = serializers.CharField(required=False)
    email_verify_url = serializers.CharField(required=False)


class UserListSerializer(serializers.Serializer):
    """
    A List serializer indicating general user attributes.
    """

    user_id = serializers.IntegerField(source="pk")
    is_active = serializers.BooleanField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    verified = serializers.BooleanField()
    phone_number = PhoneNumberSerializerField(source="account.phone_number")


class UserUpdateSerializer(serializers.Serializer):
    """
    Detail serializer for users updating their own accounts.
    Instantiated with 'partial' flag.
    """

    first_name = NameSerializerField()
    last_name = NameSerializerField()
    # Account fields
    bio = serializers.CharField()
    backup_email = serializers.EmailField()
    phone_number = PhoneNumberSerializerField()


class UserDetailSerializer(serializers.Serializer):
    """
    Detail serializer for the requesting user.
    Adds a role(s) field inteded for frontend role based access
    """
    user_id = serializers.IntegerField(source="pk")
    email = serializers.EmailField()
    first_name = NameSerializerField()
    last_name = NameSerializerField()
    joined_at = serializers.DateTimeField(source="created_at")
    email_verified = serializers.BooleanField(source="verified")
    next_email_change = serializers.DateTimeField(allow_null=True)
    phone_number = PhoneNumberSerializerField(source="account.phone_number")
    backup_email = serializers.EmailField(source="account.backup_email", allow_null=True)
    bio = serializers.CharField(source="account.bio")
    role = serializers.CharField()


class UserEmailUpdateSerializer(serializers.Serializer):
    """
    Update serializer for users to update their own emails.
    Requires email to change to and current user password.
    """

    password = serializers.CharField()
    email = serializers.EmailField()


class AdminRoleDetailSerializer(serializers.Serializer):
    """
    Requires the user object to passed as the instance to the serializer
    Role is a lazy user attribute.
    """

    user_id = serializers.IntegerField(source="pk")
    role = serializers.CharField()


class AdminRoleUpdateSerializer(serializers.Serializer):
    """
    A means to add roles to a user.
    User id is passed via the url.
    """

    role = serializers.SlugRelatedField(slug_field="name", queryset=Group.objects.all())
