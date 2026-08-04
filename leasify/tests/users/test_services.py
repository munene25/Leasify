import pytest
import typing
from datetime import timedelta

from unittest.mock import MagicMock
from freezegun import freeze_time

from django.core.mail import EmailMessage
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from leasify.tests.helpers import check_links_in_mail

from leasify.users import services as s
from leasify.users.models import User, Account, EMAIL_COOLDOWN
from leasify.users.selectors import get_group


class TestAccountCreation:

    payload = {
        "first_name": "Test",
        "last_name": "Test",
        "email": "test@mail.com",
        "password": "Pa55word!",
        "phone_number": "254710100100",
        "notify": False,
    }

    def test_account_creation_successful(self,):
        """
        Test whether account creation is successfull and data is data matches
        """
        s.user_account_create(**self.payload)
        user = User.objects.get(email=self.payload["email"])
        account = Account.objects.earliest("pk")
        # Assert reverse relationship
        assert user == account.user
        assert user.first_name == self.payload["first_name"]
        assert user.last_name == self.payload["last_name"]
        assert user.email == self.payload["email"]
        # Assert password hashed correctly
        assert user.password != self.payload["password"]
        assert account.phone_number == self.payload["phone_number"]
        user.verify_password(self.payload["password"])
        assert User.objects.count() == 1

    def test_skip_mail_sending_when_flag_set_to_false(self, django_capture_on_commit_callbacks, mailoutbox: list[EmailMessage]):
        """
        Test whether mailing will be ignored with notify flag set to false
        """
        with django_capture_on_commit_callbacks(execute=True) as callback:
            s.user_account_create(**self.payload)
        assert len(mailoutbox) == 0

    def test_mail_sent_upon_creation(self, mailoutbox: list[EmailMessage], django_capture_on_commit_callbacks):
        """
        Test normal mail sending with notify flag set to True.
        Requires always eager for delay calls
        """
        payload = {
            **self.payload,
            "notify": True,
            "unsubscribe_url": "path/to/unsubscribe",
            "email_verify_url": "path/to/verify",
        }

        with django_capture_on_commit_callbacks(execute=True):
            user = s.user_account_create(**payload)

        mail = mailoutbox[0]
        assert mail.to == [self.payload["email"]]
        check_links_in_mail(path=payload["email_verify_url"], mail=mail, with_uidb64=True, with_token=True, user=user)
        check_links_in_mail(path=payload["unsubscribe_url"], mail=mail, with_uidb64=True, user=user)

    def test_user_created_even_on_task_failure(self, monkeypatch: pytest.MonkeyPatch, django_capture_on_commit_callbacks,):
        """
        Regardless of cache failure i.e., celery cant reach broker, user should be created nonetheless
        """
        payload = {
            **self.payload,
            "notify": True,
            "unsubscribe_url": "path/to/unsubscribe",
            "email_verify_url": "path/to/verify",
        }
        mock = MagicMock()
        monkeypatch.setattr("leasify.users.tasks.send_welcome_email.delay", mock)
        mock.side_effect = Exception("Cache Down")

        with pytest.raises(Exception, match="Cache Down"):

            with django_capture_on_commit_callbacks(execute=True):
                s.user_account_create(**payload)

        assert User.objects.count() == 1

    @pytest.mark.parametrize(
        "password,exception",
        [
            ("", "short"),
            ("foo", "short"),
            ("aeiou", "short"),
            ("1235151545", "numeric"),
        ],
    )
    def test_password_validators_fail(self, password: str, exception: str):
        """
        Different variations of passwords that should fail validation
        """
        self.payload["password"] = password
        with pytest.raises(ValidationError) as exc:
            s.user_account_create(**self.payload)
        assert "password" in exc.value.detail
        assert exception in str(exc.value.detail)
        assert User.objects.count() == 0

    @pytest.mark.parametrize(
        "field,value,_password",
        [
            ("first_name", "Bethany", "Bethany!"),
            ("last_name", "Florence", "_floReNCE_"),
            ("email", "benedicturs@gmail.com", "benedictorial"),
        ],
    )
    def test_password_validators_fail_for_user_similarity(self, field: str, value: str, _password: str):
        """
        Different variations of passwords that should fail based on user similarity
        """

        self.payload[field] = value
        self.payload["password"] = _password

        with pytest.raises(ValidationError) as exc:
            s.user_account_create(**self.payload)
        assert "password" in exc.value.detail
        assert "similar" in str(exc.value.detail)
        assert User.objects.count() == 0

    @pytest.mark.parametrize(
        "field,value,duplicate",
        [
            ("email", "test@test.com", "test@test.com"),
            ("email", "phil@TEST.com", "phil@test.com"),
            ("phone_number", "0710-100-100", "+254 710 100 100"),
        ],
    )
    def test_account_creation_fails_with_db_contraints(self, field: str, value: str, phone_no: typing.Callable[..., str], duplicate: str):
        """Test that db constraints with similar values"""
        data1 = {
            "first_name": "testname",
            "last_name": "lastname",
            "email": "testemail1@gmail.com",
            "password": "Pa55word!",
            "phone_number": phone_no(),
            "notify": False,
        }
        data2 = {
            "first_name": "testname",
            "last_name": "lastname",
            "email": "testemail2@gmail.com",
            "password": "Pa55word!",
            "phone_number": phone_no(),
            "notify": False,
        }
        data1[field] = value
        data2[field] = duplicate

        s.user_account_create(**data1)
        with pytest.raises(ValidationError) as exc:
            s.user_account_create(**data2)

        assert User.objects.count() == 1
        assert field in exc.value.detail

    def test_phone_number_validator_fail_for_wrong_format(self, wrong_phone_number: str):
        """
        Assert wrong phone number formats and phone number regions are rejected
        """
        self.payload["phone_number"] = wrong_phone_number
        with pytest.raises(ValidationError) as exc:
            s.user_account_create(**self.payload)
        assert "phone_number" in exc.value.detail
        assert User.objects.count() == 0


class TestRoleAssignment:
    def test_role_assignment_succeeds(self, user: User):
        """
        A single role should be successfully added to a user
        It also should reflect in the user.role property
        """
        assert user.groups.count() == 0
        role = get_group("manager")
        s.user_set_role(user=user, role=role)

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
        mod_user = s.user_set_role(user=user, role=roles_list[0])

        with pytest.raises(RoleAssignmentError) as exc:
            s.user_set_role(user=mod_user, role=roles_list[1])
        assert "Only one role is allowed per user." in exc.value.detail
        assert mod_user.groups.count() == 1


class TestUserStatusChange:
    def test_deactivation_succeeds(self, user: User):
        """
        Check whether the returned user is deactivated
        """

        mod_user = s.user_update_active_status(user, False)
        fetched = User.objects.get(pk=user.pk)
        assert fetched == mod_user == user
        assert mod_user.is_active == False

    def test_activation_succeeds(self, user: User):
        """
        Check whether the returned user is deactivated
        """

        mod_user = s.user_update_active_status(user, True)
        fetched = User.objects.get(pk=user.pk)
        assert fetched == mod_user == user
        assert mod_user.is_active == True


class TestAccountUnsubscribe:

    @pytest.mark.parametrize("status", [True, False])
    def test_deactivation_succeeds(self, status: bool, user: User):
        """
        Account should be marked as cannot receive emails
        """

        mod_acc = s.account_update_mailing_status(user.account, status)
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
        s.user_remove_role(user=manager_user)

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
        mod_user = s.user_email_update(user=user, email=new_email, password="Pa55word!")
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
            s.user_email_update(user=user, email=new_email, password="Pa55word!")

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

        with freeze_time(before, tz_offset=0) as frozen_time:
            user.last_email_change = timezone.now()
            user.save()
            updater = lambda: s.user_email_update(user=user, email=new_email, password=password)

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
        """
        Updating existing user and account fields should succeed
        """
        data = {
            "first_name": "Some first name",
            "last_name": "Some last name",
            "phone_number": phone_no(),
        }
        mod_user = s.user_update(user, **data)
        mod_account = mod_user.account
        # assert same user returned
        assert user == mod_user
        assert user.account == mod_account

        # assert persistence
        assert User.objects.get(pk=mod_user.pk) == user
        assert mod_user.first_name == data["first_name"]
        assert mod_user.last_name == data["last_name"]
        assert mod_account.phone_number == data["phone_number"]

        # Assert key fields not mod_user
        assert mod_user.email == user.email
        assert mod_user.password == user.password

    def test_email_validation(self, user):
        """
        Emails should be normalized and incorrect changes should not reflect
        """
        backup_email = "test@GMAIl.com"
        mod_user = s.user_update(user, backup_email=backup_email)
        mod_acc = mod_user.account
        assert mod_acc.backup_email == "test@gmail.com"

        wrong_format = "test@gmail"
        with pytest.raises(ValidationError) as exc:
            s.user_update(mod_user, backup_email=wrong_format)
        assert "backup_email" in exc.value.detail

        db_version = User.objects.get(pk=user.pk)

        assert db_version.account.backup_email == "test@gmail.com"

    @pytest.mark.parametrize(
        "field, model, value",
        [
            ("backup_email", "account", "test@test.com"),
            ("bio", "account", "This is a test bio"),
            ("last_name", "user", "Guest"),
            ("first_name", "user", "Mike"),
        ],
    )
    def test_inserting_new_data_succeeds(self, field: str, model: str, value, user: User):
        """
        Originally, these fields do not exist on the db,
        User should be able to add and data
        """
        mod_user = s.user_update(user, **{field: value})
        mod_account = mod_user.account
        obj = mod_user if model == "user" else mod_account
        assert getattr(obj, field) == value

    def test_phone_number_validators_fail_for_wrong_format(self, wrong_phone_number, user):
        """
        Phone numbers that should be rejected based on incorrect countrycode
        """
        with pytest.raises(ValidationError) as exc:
            s.user_update(user, **{"phone_number": wrong_phone_number})

        assert "phone_number" in exc.value.detail

    @pytest.mark.parametrize(
        "field,value,",
        [
            ("first_name", "E"),
            ("last_name", "M"),
            ("first_name", "Edwin_"),
            ("last_name", "Munene!"),
        ],
    )
    def test_name_field_validators_fail(self, user: User, field: str, value):
        """
        Short names and unexpected punctuations are not allowed.
        """
        with pytest.raises(ValidationError) as exc:
            s.user_update(user, **{field: value})
        assert field in exc.value.detail
