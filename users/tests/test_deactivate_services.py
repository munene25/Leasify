import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from users.models import User
from users.services import user_deactivate, account_unsubscribe

class TestUserDeactivation:
    def test_deactivation_succeeds(self, user: User, django_assert_num_queries):
        """
        Very simple, just check whether the returned user is deactivated
        Also check the number of querries
        """
        with django_assert_num_queries(3):
            mod_user = user_deactivate(user)
        fetched = User.objects.get(pk=user.pk)
        assert fetched == mod_user == user
        assert mod_user.is_active == False

        with django_assert_num_queries(2):
            user_deactivate(mod_user)
        
class TestAccountUnsubscribe:
    def test_deactivation_succeeds(self, user: User, django_assert_num_queries):
        """
        Account should be marked as cannot receive emails
        Count querries
        """
        with django_assert_num_queries(3):
            mod_acc = account_unsubscribe(user.account)
        fetched = User.objects.get(pk=user.pk).account
        assert fetched == mod_acc == user.account
        assert mod_acc.can_receive_emails == False

        with django_assert_num_queries(2):
            account_unsubscribe(mod_acc)

        