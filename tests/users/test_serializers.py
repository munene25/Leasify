import pytest
from users import serializers, models
from zoneinfo import ZoneInfo


class TestUserListSerializer:
    def test_user_list_serializer_resolves_related_fields(self, user):
        """
        Assert that a list is properly serialized
        fields with "source" should resolve correctly
        """
        data = [user]
        serializer = serializers.UserListSerializer(instance=data, many=True)

        assert len(serializer.data) == 1
        s = serializer.data[0]

        assert s["user_id"] == user.pk
        assert s["phone_number"] == user.account.phone_number.as_e164

def test_user_detail_serializer_resolves_related_fields(manager_user, settings):
    u = manager_user
    manager_user.bio = "I am a test user"
    serializer = serializers.UserDetailSerializer(instance=u)
    s = dict(serializer.data)
    assert s["backup_email"] == u.account.backup_email
    assert s["email_verified"] == u.verified


    # test timezone
    local_tz = ZoneInfo(settings.TIME_ZONE)
    assert s["joined_at"] == u.created_at.astimezone(local_tz).isoformat()
    
    assert s["bio"] == u.account.bio
    # Assert null fields are still serialized
    assert s["next_email_change"] == None
    assert s["roles"] == u.roles