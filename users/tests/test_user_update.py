import pytest
from users.models import User, Account
from phonenumber_field.phonenumber import PhoneNumber
from rest_framework.exceptions import ValidationError
from dataclasses import asdict
from users.services.update import user_update

class TestUserUpdate:
    def test_updating_existing_data_succeeds(self, userdata, user: User):
        data = userdata()
        mod_user = user_update(user, **asdict(data))
        mod_account: Account = mod_user.account # type: ignore

        # assert same user returned
        assert user == mod_user
        assert user.account == mod_account # type: ignore

        # assert persistence
        assert User.objects.get(pk=mod_user.pk) == user

        assert mod_user.first_name == data.first_name
        assert mod_user.last_name == data.last_name
        
        assert mod_account.phone_number == data.phone_number

        # Assert key fields not mod_user
        assert mod_user.email ==  user.email
        assert mod_user.password == user.password

    def test_email_normalization(self, user):
        backup_email = "test@GMAIl.com"
        mod_user = user_update(user, backup_email=backup_email)
        mod_acc: Account = mod_user.account # type: ignore
        assert mod_acc.backup_email == "test@gmail.com"

    @pytest.mark.parametrize(
            "field, model, value",
            [
                ("backup_email", "account","test@test.com"),
                ("bio", "account","This is a test bio"),
                ("last_name", "user","Test"),
                ("first_name", "user","Mike"),
                ("first_name", "user","M"),
            ]
    )
    def test_inserting_and_deleting_data_succeeds(self, field, model, value, user):
        mod_user = user_update(user, **{field: value})
        mod_account: Account = mod_user.account # type: ignore
        obj = mod_user if model == "user" else mod_account
        
        # Reset  value
        value = ""

        mod_user = user_update(user, **{field: value}) # type: ignore
        mod_account: Account = mod_user.account # type: ignore
        obj = mod_user if model == "user" else mod_account

        assert getattr(obj, field) == value


    @pytest.mark.parametrize(
            "field,value",
            [
                ("phone_number", PhoneNumber.from_string("010101010101")),
                ("backup_email", "test"),
            ]
    )
    def test_update_fails_on_wrong_formats(self, field, value, user):
        with pytest.raises(ValidationError) as exc:
            user_update(user, **{field: value})

        assert field in exc.value.detail        