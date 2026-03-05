import pytest
from users.models import User
from rest_framework.exceptions import ValidationError
from users.services.update import user_update, user_change_password
from .conftest import APIPayload
from django.core.mail.message import EmailMessage


class TestUserUpdate:
    def test_updating_existing_data_succeeds(self, payload: type[APIPayload], user: User):
        """
        Updating existing user and account fields should work
        """
        data = payload()
        mod_user = user_update(user, **data.to_dict)
        mod_account = mod_user.account
        # assert same user returned
        assert user == mod_user
        assert user.account == mod_account

        # assert persistence
        assert User.objects.get(pk=mod_user.pk) == user
        assert mod_user.first_name == data.first_name
        assert mod_user.last_name == data.last_name
        assert mod_account.phone_number == data.phone_number

        # Assert key fields not mod_user
        assert mod_user.email == user.email
        assert mod_user.password == user.password

    def test_email_validation(self, user):
        """
        Emails should be normalized and incorrect changes should not reflect
        """
        backup_email = "test@GMAIl.com"
        mod_user = user_update(user, backup_email=backup_email)
        mod_acc = mod_user.account
        assert mod_acc.backup_email == "test@gmail.com"

        wrong_format = "test@gmail"
        with pytest.raises(ValidationError) as exc:
            user_update(mod_user, backup_email=wrong_format)
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
    def test_inserting_new_data_succeeds(self, field, model, value, user):
        """
        Originally, these fields do not exist on the db, 
        User should be able to add and data
        """
        mod_user = user_update(user, **{field: value})
        mod_account = mod_user.account
        obj = mod_user if model == "user" else mod_account
        assert getattr(obj, field) == value

    def test_phone_number_validators_fail_for_wrong_format(self, wrong_phone_number, user):
        """
        Phone numbers that should be rejected based on incorrect countrycode
        """
        with pytest.raises(ValidationError) as exc:
            user_update(user, **{"phone_number": wrong_phone_number})

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
    def test_name_field_validators_fail(self, user, field, value):
        """
        Short names and unexpected punctuations are not allowed.
        """
        with pytest.raises(ValidationError) as exc:
            user_update(user, **{field: value})
        assert field in exc.value.detail


class TestUserChangePassword:
    def test_password_change_successful(self, user: User) -> None:
        """
        A users password be hashed
        The new password should work pass check_password
        The old password should not work
        """
        current_password = "Pa55word!"; new_password = "TimT@tman!"
        user.check_password(current_password)
        modified = user_change_password(
            user=user,
            new_password=new_password,
            current_password=current_password
        )
        assert user == modified == User.objects.get(pk=user.pk)
        # Password should be hashed
        assert modified.password != new_password
        # Should not raise error
        modified.check_password(new_password)
        # Should raise error
        with pytest.raises(ValidationError) as exc:
            modified.check_password(current_password)
        assert "current_password" in exc.value.detail
        

    def test_password_change_sends_email(self, user: User, mailoutbox: list[EmailMessage],  django_capture_on_commit_callbacks) -> None:
        """
        Check the mail is sent to the correct user
        contains the correct subject, links, and body
        """
        from django.conf import settings


        current_password = "Pa55word!"; new_password = "TimT@tman!"
        user.check_password(current_password)
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            user_change_password(
                user=user,
                new_password=new_password,
                current_password=current_password
            )
        assert len(callbacks) == 1
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.subject == "Account password has been changed"
        assert mail.from_email == settings.DEFAULT_FROM_EMAIL
        assert mail.to == [user.email]
        assert "password-reset" in mail.body


    def test_password_changed_without_password(self, user: User):
        new_password = "Everl@sting!"
        mod_user = user_change_password(user=user, new_password=new_password)
        assert mod_user == user
        mod_user.check_password(new_password)
        
