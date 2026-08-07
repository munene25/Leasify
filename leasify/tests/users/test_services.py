import typing
from datetime import timedelta

import pytest
from unittest.mock import patch, MagicMock
from freezegun import freeze_time

from django.core.mail import EmailMessage
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from leasify.tests.helpers import check_links_in_mail

from leasify.users import services as sr
from leasify.users.choices import AccountType
from leasify.users.models import User, Account, EMAIL_COOLDOWN
from leasify.users.selectors import get_group


class TestUserCreate:

    payload = {
        "email": "test@test.com",
        "first_name": "Test",
        "last_name": "Test",
        "phone_number": "254710100100",
        "is_active": True,
        "is_staff": False,
        "is_superuser": False,
        "notify": False,
        "backup_email": "test2@test.com"
    }
    google = {
        "account_type": AccountType.GOOGLE,
        "provider_id": "xyz"
    }
    email = {
        "account_type": AccountType.EMAIL,
        "password": "Pa55word!"
    }

    def test_email_account_creation(self):
        """Should be able to create a user account of type EMAIL"""
        user = sr.user_create(**{**self.payload, **self.email})
        assert User.objects.count() == 1

        user.refresh_from_db()
        # password is hashed
        user.verify_password(self.email["password"])
        assert user.password != self.email["password"]
        assert user.account.type == AccountType.EMAIL
        assert user.account.provider_id is None
        assert user.account.phone_number == self.payload["phone_number"]
        assert user.email == self.payload["email"]
        assert user.first_name == self.payload["first_name"]
        assert user.last_name == self.payload["last_name"]
        assert user.is_staff == self.payload["is_staff"]
        assert user.is_superuser == self.payload["is_superuser"]
        assert user.is_active == self.payload["is_active"]

    def test_google_account_creation(self):
        """Should be able to create a user account of type GOOGLE"""
        user = sr.user_create(**{**self.payload, **self.google})
        assert User.objects.count() == 1

        user.refresh_from_db()
        # password is hashed
        assert not user.has_usable_password()
        assert user.account.type == AccountType.GOOGLE
        assert user.account.provider_id == "xyz"
        assert user.account.phone_number == self.payload["phone_number"]
        assert user.email == self.payload["email"]
        assert user.first_name == self.payload["first_name"]
        assert user.last_name == self.payload["last_name"]
        assert user.is_staff == self.payload["is_staff"]
        assert user.is_superuser == self.payload["is_superuser"]
        assert user.is_active == self.payload["is_active"]

    @patch("leasify.users.models.User.validate_password", return_value=True)
    def test_password_validators(self, mock: MagicMock):
        """With Email account type. Password validator has to be called"""

        sr.user_create(**{**self.payload, **self.email})
        mock.assert_called_once_with(self.email["password"])

    
    def test_email_uniqueness_enforcement(self):
        """Should validate constraints before saving in each case"""

        sr.user_create(**{**self.payload, **self.email})
        with pytest.raises(ValidationError, match="email"):
            sr.user_create(**{**self.payload, **self.google})

        assert User.objects.count() == 1

    def test_provider_id_uniqueness(self):
        """Should validate constraints before saving in each case"""

        sr.user_create(**{**self.payload, **self.google})
        with pytest.raises(ValidationError, match="provider_id"):
            sr.user_create(**{**self.payload, **self.google, "email": "test2@email.com"})

        assert User.objects.count() == 1

    def test_email_normalization(self):
        """Email should be normalized"""

        payload = {**self.payload, **self.google, "email": "TEST@TEST.COM   "}
        user = sr.user_create(**payload)
        user.refresh_from_db() # type: ignore
        assert user.email == "test@test.com"

    def test_notify_user(self, mailoutbox: list[EmailMessage], django_capture_on_commit_callbacks):
        """Notify is based on notify flag"""
        payload = {
            **self.payload, 
            **self.email, 
            "notify": True,
            "email_verify_url": "path/to/verify"
        }
        # raises for missing links
        with pytest.raises(ValidationError, match="unsubscribe_url"):
            user = sr.user_create(**payload)

        with django_capture_on_commit_callbacks(execute=True):
            user = sr.user_create(**{**payload, "unsubscribe_url": "path/to/unsub"})
        
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [user.email]
        check_links_in_mail(mail=mail, user=user, path="path/to/unsub", with_token=False, with_uidb64=True)
        check_links_in_mail(mail=mail, user =user, path="path/to/verify", with_token=True, with_uidb64=True)
    


class TestRoleAssignment:
    def test_role_assignment_succeeds(self, user: User):
        """
        A single role should be successfully added to a user
        It also should reflect in the user.role property
        """
        assert user.groups.count() == 0
        role = get_group("manager")
        sr.user_set_role(user=user, role=role)

        user.refresh_from_db()  # type: ignore

        groups = user.groups

        assert groups.count() == 1
        assert role in groups.all()
        assert user.role == role.name

    def test_multiple_role_assignment_fails(self, user: User, roles_list):
        """
        Multiple role assignments should fail raising a Rolessignmenterror.
        """
        from leasify.common.exceptions import RoleAssignmentError

        assert user.groups.count() == 0
        mod_user = sr.user_set_role(user=user, role=roles_list[0])

        with pytest.raises(RoleAssignmentError) as exc:
            sr.user_set_role(user=mod_user, role=roles_list[1])
        assert "Only one role is allowed per user." in exc.value.detail
        assert mod_user.groups.count() == 1


class TestUserStatusChange:
    def test_deactivation_succeeds(self, user: User):
        """
        Check whether the returned user is deactivated
        """

        mod_user = sr.user_update_active_status(user, False)
        fetched = User.objects.get(pk=user.pk)
        assert fetched == mod_user == user
        assert mod_user.is_active == False

    def test_activation_succeeds(self, user: User):
        """
        Check whether the returned user is deactivated
        """

        mod_user = sr.user_update_active_status(user, True)
        fetched = User.objects.get(pk=user.pk)
        assert fetched == mod_user == user
        assert mod_user.is_active == True


class TestAccountUnsubscribe:

    @pytest.mark.parametrize("status", [True, False])
    def test_deactivation_succeeds(self, status: bool, user: User):
        """
        Account should be marked as cannot receive emails
        """

        mod_acc = sr.account_update_mailing_status(user.account, status)
        mod_acc.refresh_from_db()  # type: ignore
        assert mod_acc == mod_acc == user.account
        assert mod_acc.can_receive_emails == status


class TestRoleRemoval:
    def test_role_removal_successfull(self, manager_user: User):
        """
        Test removing a role from a user and the resulting state of the user.
        """
        first_role = manager_user.role

        assert first_role is not None
        sr.user_remove_role(user=manager_user)

        manager_user.refresh_from_db()  # type: ignore

        assert manager_user.role == "regular"
        assert not manager_user.groups.exists()


class TestEmailUpdate:
    def test_email_update_succeeds(self, user: User):
        """
        Email should be normalized
        Emails should match
        Side effects like last email change and verified status are checked
        """
        new_email = "test@EXAMPLE.com"
        normalized = new_email.lower()
        mod_user = sr.user_email_update(user=user, email=new_email, password="Pa55word!")
        fetched = User.objects.get(pk=user.pk)

        assert mod_user == user == fetched
        assert mod_user.email == normalized == fetched.email

        # Check sideeffects
        assert mod_user.last_email_change is not None
        assert (mod_user.last_email_change - timezone.now()) <= timedelta(seconds=1)
        assert mod_user.next_email_change == mod_user.last_email_change + EMAIL_COOLDOWN
        assert mod_user.verified == False

    def test_email_update_with_cooldown_active_fails(self, user: User):
        """
        The cooldown should fail if user tries to change password WITHIN the cooldown window
        """
        from leasify.common.exceptions import EmailUpdateError

        new_email = "test@example.com"
        before_cooldown = EMAIL_COOLDOWN - timedelta(days=1)
        user.last_email_change = timezone.now() - before_cooldown
        user.save(update_fields=["last_email_change"])

        with pytest.raises(EmailUpdateError) as exc:
            sr.user_email_update(user=user, email=new_email, password="Pa55word!")

        assert "email" in exc.value.detail
        assert User.objects.get(pk=user.pk).email == user.email

    def test_email_update_after_cooldown_succeeds(self, user: User, password):
        """
        The cooldown should succeed if user changes password AFTER the cooldown window
        """
        from leasify.common.exceptions import EmailUpdateError

        new_email = "test@example.com"
        before = timezone.now()
        after = before + EMAIL_COOLDOWN

        with freeze_time(before) as frozen_time:
            user.last_email_change = timezone.now()
            user.save()
            updater = lambda: sr.user_email_update(user=user, email=new_email, password=password)

            with pytest.raises(EmailUpdateError) as exc:
                updater()
            assert "email" in exc.value.detail
            assert str(EMAIL_COOLDOWN.days) in str(exc.value.detail)

            frozen_time.move_to(after)
            assert timezone.now() == after
            assert user.next_email_change is None

            mod_user = updater()
            assert mod_user == user
            assert mod_user.last_email_change == timezone.now()
            assert mod_user.email == new_email


class TestUserUpdate:
    def test_updating_existing_data_succeeds(self, user: User, phone_no: typing.Callable[..., typing.Any]):
        """Updating existing user and account fields should succeed"""
        data = {
            "first_name": "First",
            "last_name": "Last",
            "phone_number": phone_no(),
            "backup_email": "   Test@TEST.cOM  "
        }
        modified = sr.user_update(user, **data)
        user.refresh_from_db() # type: ignore
        assert user == modified
        assert user.first_name == data["first_name"]
        assert user.last_name == data["last_name"]
        assert user.account.phone_number == data["phone_number"]
        assert user.account.backup_email == "test@test.com"


    def test_validators(self, user: User):
        """
        Phone numbers that should be rejected based on incorrect countrycode
        """
        with pytest.raises(ValidationError, match="phone_number"):
            sr.user_update(user, phone_number="200")

        with pytest.raises(ValidationError, match="first_name"):
            sr.user_update(user, first_name="E")

