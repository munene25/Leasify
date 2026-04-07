import pytest
from zoneinfo import ZoneInfo
from rest_framework.exceptions import ValidationError
from users import serializer, models



class TestUserListSerializer:
    def test_user_list_serializer_resolves_related_fields(self, user: models.User):
        """
        Assert that a list is properly serialized
        fields with "source" should resolve correctly
        """
        data = [user]
        s = serializer.UserListSerializer(instance=data, many=True)

        assert len(s.data) == 1
        s = s.data[0]

        assert s["user_id"] == user.pk
        assert s["phone_number"] == user.account.phone_number


class TestUserDetailSerializer:
    def test_resolves_related_fields(self, manager_user):
        """
        Tests the UserDetailSerializer
        Asserts fields with source are populated correctly

        """

        u = manager_user
        bio = "I am a test user"
        manager_user.account.bio = bio
        instance = serializer.UserDetailSerializer(instance=u)
        s = dict(instance.data)
        assert s["backup_email"] == u.account.backup_email
        assert s["email_verified"] == u.verified
        assert s["bio"] == bio == u.account.bio
        # Assert null fields are present and serialized
        assert s["next_email_change"] == None
        assert s["role"] == u.role

    def test_datetime_fields_resolve_with_defined_timezone(self, manager_user, settings):
        """
        Added a test to check how datetime formats are serialized.
        Should be converted to the timezone setting.
        """
        # test timezone
        u = manager_user
        manager_user.bio = "I am a test user"
        instance = serializer.UserDetailSerializer(instance=u)
        s = dict(instance.data)
        local_tz = ZoneInfo(settings.TIME_ZONE)
        assert s["joined_at"] == u.created_at.astimezone(local_tz).isoformat()


class TestBasePasswordSerializer:
    def test_serializer_validation_succeeds(self):
        data = {"new_password": "password", "confirm_password": "password"}
        instance = serializer.BasePasswordSerializer(data=data)
        instance.is_valid(raise_exception=True)

        s = instance.validated_data
        assert isinstance(s, dict)
        assert len(s) == 1
        assert "new_password" in data

    def test_serializer_validation_fails(self):
        data = {"new_password": "password", "confirm_password": "Password"}
        instance = serializer.BasePasswordSerializer(data=data)
        with pytest.raises(ValidationError) as exc:
            instance.is_valid(raise_exception=True)
        assert "confirm_password" in exc.value.detail


class TestUpdateSerializer:
    def test_serializer_ommits_unnamed_fields(self):
        from tests.types import UserUpdatePayload

        data: UserUpdatePayload = {
            "first_name": "Fred",
            "last_name": "Gradle",
        }
        instance = serializer.UserUpdateSerializer(data=data, partial=True)
        instance.is_valid(raise_exception=True)
        s = instance.validated_data
        assert isinstance(s, dict)
        assert ["first_name", "last_name"] == list(s.keys())


class TestPasswordChangeSerializer:
    def test_serializer(self):
        data = {"password": "password", "new_password": "password", "confirm_password": "password"}
        instance = serializer.PasswordChangeSerializer(data=data)
        instance.is_valid(raise_exception=True)

        s = instance.validated_data
        assert isinstance(s, dict)
        assert len(s) == 2
        assert {"password", "new_password"} == set(s.keys())


class TestUserRoleDetialSerializer:
    def test_role_is_serialized_correctly(self, manager_user):
        """Moving from multiple roles to singular role per user"""
        instance = serializer.UserRoleDetailSerializer(instance=manager_user)
        s = dict(instance.data)
        assert s["role"] == manager_user.role


class TestUserRoleCreateSerializer:
    def test_role_is_retrieved_correctly(self, get_role):
        """Serializer data should be converted to a role instance"""
        role = get_role("tenant")
        instance = serializer.UserRoleCreateSerializer(data={"role": "tenant"})
        assert instance.is_valid()
        s = instance.validated_data
        assert isinstance(s, dict)
        assert s["role"] == role

