import pytest
import typing
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from django.core.mail import EmailMessage
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from users.models import User, Account, EMAIL_COOLDOWN
from freezegun import freeze_time
from users import services as s
from tests.types import UserCreatePayload
from users.selectors import get_group


class TestAccountCreation:
    def test_account_creation_successful(self, user_create_payload: UserCreatePayload):
        """
        Test whether account creation is successfull and data is data matches
        """
        s.user_account_create(**user_create_payload)
        user = User.objects.get(email=user_create_payload["email"])
        account = Account.objects.earliest("pk")
        # Assert reverse relationship
        assert user == account.user
        assert user.first_name == user_create_payload["first_name"]
        assert user.last_name == user_create_payload["last_name"]
        assert user.email == user_create_payload["email"]
        # Assert password hashed correctly
        assert user.password != user_create_payload["password"]
        assert account.phone_number == user_create_payload["phone_number"]
        user.validate_password(user_create_payload["password"])
        assert User.objects.count() == 1

    def test_skip_mail_sending_when_flag_set_to_false(
        self,
        user_create_payload: UserCreatePayload,
        django_capture_on_commit_callbacks,
    ):
        """
        Test whether mailing will be ignored with notify flag set to false
        """
        with django_capture_on_commit_callbacks() as callback:
            s.user_account_create(**user_create_payload)
        assert len(callback) == 0
        assert User.objects.count() == 1

    def test_mail_sent_upon_creation(
        self,
        user_create_payload: UserCreatePayload,
        mailoutbox,
        django_capture_on_commit_callbacks,
    ):
        """
        Test normal mail sending with notify flag set to True.
        Requires always eager for delay calls
        """
        from common.emails import email_context

        user_create_payload["notify"] = True

        with django_capture_on_commit_callbacks() as callback:
            s.user_account_create(**user_create_payload)
        assert User.objects.count() == 1
        # Assert callback stores the mail sender
        assert len(callback) == 1
        # Execute callback
        callback[0]()
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [user_create_payload["email"]]
        assert mail.from_email == email_context.default_from_email
        assert mail.subject == f"Welcome to {email_context.app_name}"
        assert "email-verify" in mail.body

    @patch("users.tasks.send_welcome_email.delay")
    def test_user_creation_success_on_cache_fail(
        self,
        mock,
        user_create_payload: UserCreatePayload,
        django_capture_on_commit_callbacks,
    ):
        """
        Regardless of cache failure i.e., celery cant reach broker, user should be created nonetheless
        """
        # Cache raises an exception
        user_create_payload["notify"] = True
        mock.side_effect = Exception("Cache Down")

        with pytest.raises(Exception, match="Cache Down"):

            with django_capture_on_commit_callbacks(execute=True):
                s.user_account_create(**user_create_payload)

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
    def test_password_validators_fail(self, user_create_payload: UserCreatePayload, password, exception):
        """
        Different variations of passwords that should fail validation
        """
        user_create_payload["password"] = password
        with pytest.raises(ValidationError) as exc:
            s.user_account_create(**user_create_payload)
        assert "password" in exc.value.detail
        assert exception in str(exc.value.detail)
        assert User.objects.count() == 0

    @pytest.mark.parametrize(
        "field,value,password",
        [
            ("first_name", "Bethany", "Bethany!"),
            ("last_name", "Florence", "_floReNCE_"),
            ("email", "benedicturs@gmail.com", "benedictorial"),
        ],
    )
    def test_password_validators_fail_for_user_similarity(
        self, user_create_payload: UserCreatePayload, field, value, password
    ):
        """
        Different variations of passwords that should fail based on user similarity
        """

        user_create_payload[field] = value
        user_create_payload["password"] = password

        with pytest.raises(ValidationError) as exc:
            s.user_account_create(**user_create_payload)
        assert "password" in exc.value.detail
        assert "similar" in str(exc.value.detail)
        assert User.objects.count() == 0

    @pytest.mark.parametrize(
        "field,value,duplicate",
        [
            ("email", "test@test.com", "test@test.com"),
            ("email", "phil@TEST.com", "phil@test.com"),
            (
                "phone_number",
                "0710-100-100",
                "+254 710 100 100",
            ),
        ],
    )
    def test_account_creation_fails_with_db_contraints(
        self,
        field: str,
        value: str,
        phone_no,
        duplicate,
    ):
        """
        Test that db constraints with multiple
        """
        data1: UserCreatePayload = {
            "first_name": "testname",
            "last_name": "lastname",
            "email": "testemail1@gmail.com",
            "password": "Pa55word!",
            "phone_number": phone_no(),
            "notify": False,
        }
        data2: UserCreatePayload = {
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

    def test_phone_number_validator_fail_for_wrong_format(
        self,
        user_create_payload: UserCreatePayload,
        wrong_phone_number: str,
    ):
        """
        Assert wrong phone number formats and phone number regions are rejected
        """
        user_create_payload["phone_number"] = wrong_phone_number
        with pytest.raises(ValidationError) as exc:
            s.user_account_create(**user_create_payload)
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
        from common.exceptions import RoleAssignmentError

        assert user.groups.count() == 0
        mod_user = s.user_set_role(user=user, role=roles_list[0])

        with pytest.raises(RoleAssignmentError) as exc:
            s.user_set_role(user=mod_user, role=roles_list[1])
        assert "Only one role is allowed per user." in exc.value.detail
        assert mod_user.groups.count() == 1


class TestUserDeactivation:
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
        from common.exceptions import EmailUpdateError

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
        from common.exceptions import EmailUpdateError

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


class TestUserEmailVerifyConfirmation:
    def test_email_set_as_verified(self, user: User):
        """
        Verified status should reflect
        """
        mod_user = s.user_email_verify(user)
        mod_user.refresh_from_db()  # type: ignore
        assert mod_user == user
        assert mod_user.verified == True


class TestLoginService:
    def test_authenticate_service_succeeds(self, user: User, password: str):
        """
        credentials passed should correctly return an authenticated user
        last_login field should be updated
        returned user should be the match
        """
        authenticated_user = s.user_authenticate(email=user.email, password=password)
        assert authenticated_user == user

    def test_login_service_fails_with_inactive_users(self, user: User):
        user.is_active = False
        user.save(update_fields=["is_active"])

        with pytest.raises(AuthenticationFailed) as exc:
            s.user_authenticate(email=user.email, password="Pa55word!")
        assert "email" in exc.value.detail and "password" in exc.value.detail

    def test_login_fails_for_wrong_credentials(self, user: User):
        wrong_email = "test@testemail.com"
        wrong_pass = "password"
        with pytest.raises(AuthenticationFailed) as exc:
            s.user_authenticate(email=wrong_email, password=wrong_pass)
        assert "email" in exc.value.detail and "password" in exc.value.detail

    def test_login_succeds_with_normalization(self, user: User):
        """
        User lookups should use normalized emails
        """
        parts = user.email.split("@")
        email = parts[0] + "@" + parts[1].upper()
        authd_user = s.user_authenticate(email=email, password="Pa55word!")
        assert authd_user == user


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


class TestUserChangePassword:
    def test_password_change_successful(self, user: User) -> None:
        """
        A users password be hashed
        The new password should work pass check_password
        The old password should not work
        """
        current_password = "Pa55word!"
        new_password = "TimT@tman!"
        user.validate_password(current_password)
        modified = s.user_change_password(user=user, new_password=new_password, password=current_password)
        assert user == modified == User.objects.get(pk=user.pk)
        # Password should be hashed
        assert modified.password != new_password
        # Should not raise error
        modified.validate_password(new_password)
        # Should raise error
        with pytest.raises(ValidationError) as exc:
            modified.validate_password(current_password)
        assert "password" in exc.value.detail

    def test_password_change_sends_email(
        self,
        user: User,
        mailoutbox: list[EmailMessage],
        django_capture_on_commit_callbacks,
    ) -> None:
        """
        Check the mail is sent to the correct user
        contains the correct subject, links, and body
        """
        from common.emails import email_context

        current_password = "Pa55word!"
        new_password = "TimT@tman!"
        user.validate_password(current_password)
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            s.user_change_password(user=user, new_password=new_password, password=current_password)
        assert len(callbacks) == 1
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.subject == "Account password has been changed"
        assert mail.from_email == email_context.default_from_email
        assert mail.to == [user.email]
        assert "password-reset" in mail.body

    def test_password_changed_without_password(self, user: User):
        new_password = "Everl@sting!"
        mod_user = s.user_change_password(user=user, new_password=new_password, is_ressetting=True)
        assert mod_user == user
        mod_user.validate_password(new_password)
