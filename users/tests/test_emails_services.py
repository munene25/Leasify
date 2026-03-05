import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from users.models import User, EMAIL_COOLDOWN
from users.services import user_email_update, user_email_verify


class TestEmailUpdate:
    def test_email_update_succeeds(self, user: User):
        new_email = "test@EXAMPLE.com"
        normalized = new_email.lower()
        mod_user = user_email_update(user=user, email=new_email, password="Pa55word!")
        fetched = User.objects.get(pk=user.pk)

        assert mod_user == user == fetched
        assert mod_user.email == normalized == fetched.email

        # Check sideeffects
        assert mod_user.last_email_change is not None
        assert (mod_user.last_email_change - timezone.now()) <= timedelta(seconds=1) 
        assert mod_user.next_email_change == mod_user.last_email_change + EMAIL_COOLDOWN
        assert mod_user.verified == False

    def test_email_update_with_cooldown_active_fails(self, user: User):
        new_email = "test@example.com"
        before_cooldown = EMAIL_COOLDOWN - timedelta(days=1)
        user.last_email_change = timezone.now() - before_cooldown
        user.save(update_fields=["last_email_change"])

        with pytest.raises(ValidationError) as exc:
            user_email_update(user=user, email=new_email, password="Pa55word!")

        assert "email" in exc.value.detail
        assert User.objects.get(pk=user.pk).email == user.email

    def test_email_update_after_cooldown_succeeds(self, user: User):
        new_email = "test@example.com"
        after_cooldown = EMAIL_COOLDOWN + timedelta(days=1)
        user.last_email_change = timezone.now() - after_cooldown
        user.save(update_fields=["last_email_change"])
        mod_user = user_email_update(user=user, email=new_email, password="Pa55word!")
        
        fetched = User.objects.get(pk=user.pk)
        assert fetched == mod_user
        assert mod_user.email == new_email

class TestConfirmEmailVerify:
    def test_email_set_as_verified(self, user: User, django_assert_num_queries):
        """
        Also have to consider the transaction savepoints
        """
        with django_assert_num_queries(3):
            user = user_email_verify(user)
        assert user.verified == True

        with django_assert_num_queries(2) as cap:
            user_email_verify(user)

